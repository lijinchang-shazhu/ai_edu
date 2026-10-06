"""交互式网页课件（网页 PPT）——数据驱动幻灯片引擎。

大模型只负责产出「幻灯片内容」（JSON），本模块用统一的专业幻灯片框架渲染成
多页、带封面、可翻页、含交互组件与学情埋点的网页 PPT，保证每次生成都规范一致。

幻灯片类型：cover / objectives / content / choice / judge / drag / fill / explore / summary
"""
import random
import re

DECK_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>交互式课件 · __TITLE__</title>
<style>
  :root{--bg:#f4f6fb;--ink:#1e293b;--muted:#64748b;--primary:#4f46e5;--primary-soft:#eef2ff;--card:#fff;--ok:#10b981;--bad:#ef4444;--ring:#e2e8f0}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'PingFang SC','Microsoft YaHei','Segoe UI',sans-serif;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased}
  .stage{max-width:920px;margin:0 auto;padding:24px 20px 96px}
  .topbar{position:fixed;top:0;left:0;right:0;height:4px;background:var(--ring);z-index:20}
  .topbar i{display:block;height:100%;background:linear-gradient(90deg,var(--primary),#7c5cf0);transition:width .3s}
  .slide{display:none;animation:fade .25s ease}
  .slide.active{display:block}
  @keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .card{background:var(--card);border:1px solid var(--ring);border-radius:16px;padding:32px;box-shadow:0 1px 2px rgba(15,23,42,.05)}
  h1{font-size:32px;font-weight:700;letter-spacing:-.5px}
  h2{font-size:20px;font-weight:600;margin-bottom:20px}
  .lead{color:var(--muted);line-height:1.7}
  .cover{text-align:center;padding:72px 32px;position:relative;overflow:hidden}
  .cover::before{content:'';position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--primary),#7c5cf0,#10b981)}
  .cover .kicker{display:inline-block;padding:6px 14px;border-radius:999px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:600;margin-bottom:22px}
  .cover h1{font-size:40px;margin-bottom:14px}
  .cover p{color:var(--muted)}
  .obj{display:flex;gap:12px;padding:16px;border-radius:12px;background:#f8fafc;margin-bottom:12px;align-items:flex-start}
  .obj b{color:var(--primary);min-width:76px;flex-shrink:0}
  .grid{display:grid;gap:12px}
  .kcard{border:1px solid var(--ring);border-radius:12px;padding:16px;cursor:pointer;transition:.15s}
  .kcard:hover{border-color:var(--primary);background:var(--primary-soft)}
  .kcard .a{display:none;color:var(--muted);font-size:14px;margin-top:8px;line-height:1.7}
  .kcard.open .a{display:block}
  .opt{display:block;width:100%;text-align:left;padding:14px 16px;border:1.5px solid var(--ring);border-radius:12px;margin:10px 0;cursor:pointer;font-size:15px;transition:.15s;background:#fff}
  .opt:hover{border-color:var(--primary)}
  .opt.sel{border-color:var(--primary);background:var(--primary-soft)}
  .opt.ok{border-color:var(--ok);background:#ecfdf5}
  .opt.no{border-color:var(--bad);background:#fef2f2}
  .judge-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 16px;border:1px solid var(--ring);border-radius:12px;margin:10px 0}
  .btn{border:1px solid var(--ring);background:#fff;color:var(--ink);padding:8px 18px;border-radius:9px;cursor:pointer;font-size:14px;transition:.15s}
  .btn:hover{border-color:var(--primary);color:var(--primary)}
  .btn.primary{background:var(--primary);border-color:var(--primary);color:#fff}
  .btn.primary:hover{opacity:.92;color:#fff}
  .btn.on{border-color:var(--primary);background:var(--primary-soft);color:var(--primary)}
  .btn.ok{border-color:var(--ok);background:#ecfdf5;color:var(--ok)}
  .btn.no{border-color:var(--bad);background:#fef2f2;color:var(--bad)}
  .drag-row{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
  .drag-item{background:#eef2ff;border:1px solid var(--ring);padding:12px 18px;border-radius:10px;cursor:grab;user-select:none}
  input[type=text],textarea{width:100%;padding:12px;border:1.5px solid var(--ring);border-radius:10px;font-size:15px;font-family:inherit}
  input:focus,textarea:focus{outline:none;border-color:var(--primary)}
  .feedback{font-size:13px;margin-top:8px;min-height:18px}
  .poll{display:flex;gap:10px;margin:12px 0}
  .poll .opt{flex:1;text-align:center}
  .nav{position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-top:1px solid var(--ring);padding:14px 20px;display:flex;align-items:center;justify-content:space-between}
  .dots{display:flex;gap:6px}
  .dots span{width:8px;height:8px;border-radius:99px;background:#cbd5e1;transition:.2s}
  .dots span.on{width:22px;background:var(--primary)}
  .nav .page{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
  .tracker{position:fixed;right:16px;bottom:70px;background:#0f172a;color:#fff;padding:8px 14px;border-radius:12px;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.2)}
  .tracker b{color:#7dd3fc}
  .match-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .match-item{padding:12px 16px;border:1.5px solid var(--ring);border-radius:10px;margin:8px 0;cursor:pointer;font-size:14px;transition:.15s}
  .match-item:hover{border-color:var(--primary)}
  .match-item.sel{border-color:var(--primary);background:var(--primary-soft)}
  .match-item.ok{border-color:var(--ok);background:#ecfdf5}
  .match-item.no{border-color:var(--bad);background:#fef2f2}
  .step{padding:12px 0;border-bottom:1px solid var(--ring);opacity:.35;transition:opacity .3s}
  .step.on{opacity:1}
  .step b{display:block;font-size:15px;margin-bottom:4px}
  .step .step-body{color:var(--muted);font-size:14px;line-height:1.7;display:none}
  .step.on .step-body{display:block}
  .sliders{display:flex;flex-wrap:wrap;gap:16px;margin-top:14px}
  .slider-item{flex:1;min-width:120px}
  .slider-item label{display:block;font-size:13px;color:var(--muted);margin-bottom:4px}
  .slider-item input[type=range]{width:100%;accent-color:var(--primary)}
  canvas.graph-canvas{width:100%;border:1px solid var(--ring);border-radius:10px;background:#fff}
  @media print{.nav,.topbar,.tracker{display:none!important}.slide{display:block!important;page-break-after:always}.stage{max-width:none;padding:0}body{background:#fff}}
</style>
</head>
<body>
<div class="topbar"><i id="bar"></i></div>
<div class="stage">
__SLIDES__
</div>

<div class="nav">
  <button class="btn" id="prev" onclick="go(-1)">← 上一页</button>
  <div style="display:flex;align-items:center;gap:14px">
    <div class="dots" id="dots"></div>
    <span class="page" id="page">1</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px">
    <button class="btn" onclick="window.print()">导出 PDF</button>
    <button class="btn" id="next" onclick="go(1)">下一页 →</button>
  </div>
</div>

__TRACKER__

<script>
  var CID = "__CID__";
  var STUDENT = "stu_" + Math.random().toString(36).slice(2, 6);
  var TOTAL = document.querySelectorAll(".slide").length;
  var cur = 0;
  var tracks = [];
  var attempts = {};
  function track(qid, component, action, value, extra){
    attempts[qid] = (attempts[qid] || 0) + 1;
    var e = {coursewareId: CID, qid: qid, component: component, action: action, value: value, student: STUDENT, attempt: attempts[qid]};
    if(extra){ for(var k in extra){ e[k] = extra[k]; } }
    tracks.push(e);
    var c = document.getElementById("count"); if(c){ c.innerText = tracks.length; }
    try{ fetch("/api/learning/track", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(e)}); }catch(err){}
    return e;
  }
  function render(){
    var slides = document.querySelectorAll(".slide");
    slides.forEach(function(s,i){ s.classList.toggle("active", i===cur); });
    document.getElementById("bar").style.width = ((cur+1)/TOTAL*100) + "%";
    document.getElementById("page").innerText = (cur+1) + " / " + TOTAL;
    document.getElementById("prev").disabled = cur===0;
    document.getElementById("next").disabled = cur===TOTAL-1;
    var dots = document.getElementById("dots"); dots.innerHTML = "";
    for(var i=0;i<TOTAL;i++){ var d=document.createElement("span"); if(i===cur)d.className="on"; dots.appendChild(d); }
  }
  function go(d){ cur = Math.max(0, Math.min(TOTAL-1, cur+d)); render(); window.scrollTo({top:0,behavior:"smooth"}); }
  document.addEventListener("keydown", function(e){ if(e.key==="ArrowRight")go(1); if(e.key==="ArrowLeft")go(-1); });

  function expand(el, qid){ el.classList.toggle("open"); track(qid, "expand", el.classList.contains("open")?"open":"close", ""); }
  function choose(el){
    var opts = el.parentElement.querySelectorAll(".opt"); opts.forEach(function(o){ o.classList.remove("sel","ok","no"); });
    el.classList.add("sel");
    var correct = el.dataset.answer === "1";
    var qid = el.dataset.q;
    track(qid, "choice", "select", el.innerText.trim(), {correct: correct?1:0});
    var fb = document.getElementById("fb-"+qid);
    if(fb){ fb.innerText = correct ? "✅ 回答正确" : "❌ 再想想，试试其它选项"; fb.style.color = correct ? "var(--ok)" : "var(--bad)"; }
    opts.forEach(function(o){ if(o.dataset.answer==="1"){ o.classList.add("ok"); } });
  }
  function judge(btn){
    var row = btn.closest(".judge-row"); var qid = row.dataset.q;
    var btns = row.querySelectorAll(".btn"); btns.forEach(function(b){ b.classList.remove("on","ok","no"); });
    btn.classList.add("on");
    var isTrue = btn.dataset.val === "1";
    var correct = isTrue === (row.dataset.answer === "1");
    track(qid, "judge", "click", btn.innerText.trim(), {correct: correct?1:0});
    btns.forEach(function(b){ if(b===btn){ b.classList.add(correct?"ok":"no"); } });
  }
  var dragRow = null, dragEl = null;
  document.addEventListener("dragstart", function(e){ if(e.target.classList.contains("drag-item")){ dragEl = e.target; dragRow = e.target.parentElement; e.target.style.opacity=".5"; } });
  document.addEventListener("dragend", function(e){ e.target.style.opacity="1"; track(e.target.dataset.q, "drag", "reorder", e.target.dataset.step); });
  document.addEventListener("dragover", function(e){ if(!e.target.classList.contains("drag-row")) return; e.preventDefault(); var after=getDragAfter(e.target,e.clientX); if(after==null)e.target.appendChild(dragEl); else e.target.insertBefore(dragEl,after); });
  function getDragAfter(c,x){ var items=[].slice.call(c.querySelectorAll(".drag-item")); return items.reduce(function(cl,ch){ var b=ch.getBoundingClientRect(); var o=x-b.left-b.width/2; if(o<0&&o>cl.offset)return{offset:o,element:ch}; return cl; },{offset:Number.NEGATIVE_INFINITY}).element; }
  function checkDrag(row){
    var order=[].map.call(row.querySelectorAll(".drag-item"), function(e){ return e.dataset.step; }).join("");
    var correct = order === row.dataset.answer;
    track(row.dataset.q, "drag", "check", order, {correct: correct?1:0});
    var fb=document.getElementById("fb-"+row.dataset.q); if(fb){ fb.innerText=correct?"✅ 顺序正确":"❌ 顺序不正确，再试试"; fb.style.color=correct?"var(--ok)":"var(--bad)"; }
  }
  function checkFill(input){
    var v=input.value.trim(); var correct = v.length>2;
    track(input.dataset.q, "fill", "submit", v, {correct: correct?1:0});
    var fb=document.getElementById("fb-"+input.dataset.q); if(fb){ fb.innerText=correct?"✅ 已记录你的理解":"请认真填写你的理解"; fb.style.color=correct?"var(--ok)":"var(--bad)"; }
  }
  function vote(el){
    var opts=el.parentElement.querySelectorAll(".opt"); opts.forEach(function(o){o.classList.remove("sel");}); el.classList.add("sel");
    track(el.dataset.q, "vote", "select", el.innerText.trim());
  }
  function nextStep(btn){
    var steps = btn.closest('.card').querySelectorAll('.step');
    for(var i=0;i<steps.length;i++){
      if(!steps[i].classList.contains('on')){ steps[i].classList.add('on'); track(steps[i].dataset.q,'steps','reveal',i+1); break; }
    }
  }
  var matchSel = null;
  function matchPick(el){
    if(el.classList.contains("left")){
      var prev = el.closest(".match-grid").querySelector(".left.sel");
      if(prev) prev.classList.remove("sel");
      el.classList.add("sel");
      matchSel = el;
      track(el.dataset.q, "match", "pick", el.dataset.idx);
    } else if(el.classList.contains("right") && matchSel){
      var left = matchSel;
      var correct = left.dataset.idx === el.dataset.idx;
      track(el.dataset.q, "match", "pair", left.dataset.idx + "-" + el.dataset.idx, {correct: correct?1:0});
      el.classList.add(correct ? "ok" : "no");
      left.classList.add(correct ? "ok" : "no");
      left.classList.remove("sel");
      matchSel = null;
    }
  }
  function submitAll(){
    track("summary", "submit", "click", "submit");
    document.getElementById("summary").innerText = "已采集 " + tracks.length + " 次课堂交互，数据将回流至教师个人教学记忆库，用于优化下一轮备课。";
  }
  function getVal(id){ var e=document.getElementById(id); return e?parseFloat(e.value):0; }
  function redrawGraph(idx){
    var canvas=document.getElementById('graph_'+idx); if(!canvas)return;
    var ctx=canvas.getContext('2d'); var w=canvas.width, h=canvas.height;
    var fn=canvas.dataset.fn||'quadratic';
    var xmin=-6,xmax=6,ymin=-6,ymax=6;
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle='#eef2f7'; ctx.lineWidth=1;
    for(var i=xmin;i<=xmax;i++){ var gx=(i-xmin)/(xmax-xmin)*w; ctx.beginPath(); ctx.moveTo(gx,0); ctx.lineTo(gx,h); ctx.stroke(); }
    for(var j=ymin;j<=ymax;j++){ var gy=h-(j-ymin)/(ymax-ymin)*h; ctx.beginPath(); ctx.moveTo(0,gy); ctx.lineTo(w,gy); ctx.stroke(); }
    ctx.strokeStyle='#94a3b8';
    var cx=(0-xmin)/(xmax-xmin)*w, cy=h-(0-ymin)/(ymax-ymin)*h;
    ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(w,cy); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx,0); ctx.lineTo(cx,h); ctx.stroke();
    function px(x){ return (x-xmin)/(xmax-xmin)*w; }
    function py(y){ return h-(y-ymin)/(ymax-ymin)*h; }
    function fy(x){
      if(fn==='quadratic'){ var a=getVal('pa_'+idx),b=getVal('pb_'+idx),c=getVal('pc_'+idx); return a*x*x+b*x+c; }
      if(fn==='linear'){ var k=getVal('pk_'+idx),b2=getVal('pb_'+idx); return k*x+b2; }
      if(fn==='sin'){ var A=getVal('pA_'+idx),w2=getVal('pw_'+idx),p=getVal('pp_'+idx); return A*Math.sin(w2*x+p); }
      return 0;
    }
    ctx.strokeStyle='#4f46e5'; ctx.lineWidth=2.5; ctx.beginPath();
    var first=true;
    for(var x=xmin;x<=xmax;x+=0.05){
      var y=fy(x);
      if(y<ymin-1||y>ymax+1){ first=true; continue; }
      if(first){ ctx.moveTo(px(x),py(y)); first=false; } else ctx.lineTo(px(x),py(y));
    }
    ctx.stroke();
  }
  var _proj={};
  function launchProjectile(idx){
    var canvas=document.getElementById('phys_'+idx); if(!canvas)return;
    if(_proj[idx]) cancelAnimationFrame(_proj[idx]);
    var ctx=canvas.getContext('2d'); var w=canvas.width, h=canvas.height;
    var v=getVal('psp_'+idx), ang=getVal('pan_'+idx)*Math.PI/180, g=9.8;
    var vx=v*Math.cos(ang), vy=v*Math.sin(ang);
    var scale=3.0, t=0, dt=0.02, x0=24, y0=h-24;
    function frame(){
      ctx.clearRect(0,0,w,h);
      ctx.strokeStyle='#cbd5e1'; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(0,h-24); ctx.lineTo(w,h-24); ctx.stroke();
      var x=x0+vx*scale*t, y=y0-(vy*scale*t-0.5*g*scale*t*t);
      ctx.strokeStyle='#4f46e5'; ctx.lineWidth=1.5; ctx.beginPath();
      for(var tt=0;tt<=t;tt+=0.02){
        var xx=x0+vx*scale*tt, yy=y0-(vy*scale*tt-0.5*g*scale*tt*tt);
        if(yy>h-24) break;
        if(tt===0) ctx.moveTo(xx,yy); else ctx.lineTo(xx,yy);
      }
      ctx.stroke();
      ctx.fillStyle='#4f46e5'; ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2); ctx.fill();
      t+=dt;
      if(y<h-24 && x<w-10){ _proj[idx]=requestAnimationFrame(frame); }
    }
    _proj[idx]=requestAnimationFrame(frame);
  }
  function resetProjectile(idx){
    if(_proj[idx]) cancelAnimationFrame(_proj[idx]);
    var canvas=document.getElementById('phys_'+idx); if(!canvas)return;
    var ctx=canvas.getContext('2d'); ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.strokeStyle='#cbd5e1'; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(0,canvas.height-24); ctx.lineTo(canvas.width,canvas.height-24); ctx.stroke();
  }
  function initGraphs(){
    var cs = document.querySelectorAll('canvas[id^="graph_"]');
    cs.forEach(function(c){ redrawGraph(parseInt(c.id.split('_')[1])); });
  }
  initGraphs();
  render();
</script>
</body>
</html>
"""


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _slider(idx, name, label, vmin, vmax, step, default) -> str:
    """生成一个参数滑块（变量探索器）。"""
    return (
        f'<div class="slider-item"><label>{_esc(label)}</label>'
        f'<input type="range" id="p{name}_{idx}" min="{vmin}" max="{vmax}" step="{step}" value="{default}" oninput="redrawGraph({idx})"></div>'
    )


def build_default_deck(topic: str) -> dict:
    """默认幻灯片内容（离线演示 / 解析失败回退时使用）—— 以「教学讲解」为主。"""
    return {
        "title": topic,
        "subtitle": "教学演示",
        "slides": [
            {"type": "cover"},
            {
                "type": "objectives",
                "items": [
                    f"理解并掌握「{topic}」的核心概念与基本方法",
                    "通过自主探究与合作学习，发展学科核心素养",
                    "激发学习兴趣，培养严谨求实的科学态度",
                ],
            },
            {
                "type": "steps",
                "heading": f"原理讲解 · {topic}",
                "steps": [
                    {"title": "第一步 · 情境导入", "body": f"从生活实例引出「{topic}」，明确要研究的问题。"},
                    {"title": "第二步 · 概念建构", "body": f"逐步推导「{topic}」的核心概念与方法，理解其本质。"},
                    {"title": "第三步 · 迁移应用", "body": f"结合数形结合，把「{topic}」应用到具体问题中，体会学以致用。"},
                ],
            },
            {
                "type": "graph",
                "heading": "数形结合 · 函数图像",
                "note": "拖动参数 a、b、c，观察图像变化，理解函数图像与系数的关系",
                "function": "quadratic",
            },
            {
                "type": "physics",
                "heading": "抛体运动机理演示",
                "note": "调整初速度和发射角，点击「发射」观察抛物线轨迹",
            },
            {
                "type": "summary",
                "points": [
                    f"掌握「{topic}」核心概念与方法",
                    "经历探究过程，理解数形结合",
                    "课后完成分层练习，及时反馈",
                ],
            },
        ],
    }


QUESTION_TYPES = {"choice", "judge", "drag", "fill", "match", "vote"}


def split_deck(deck: dict):
    """把 deck 拆成 (教学页, 互动练习页)。教学页不含任何题目。"""
    teaching = []
    interactive = []
    for s in deck.get("slides", []):
        if s.get("type") in QUESTION_TYPES:
            interactive.append(s)
        else:
            teaching.append(s)
    return teaching, interactive


def build_interactive_deck(topic: str) -> dict:
    """随堂互动练习课件（学情采集）：选择/判断/拖拽/填空 + 埋点。"""
    return {
        "title": f"{topic} · 随堂互动练习",
        "subtitle": "互动练习",
        "slides": [
            {"type": "cover", "kicker": "随堂互动", "subtitle": "互动练习 · 系统采集课堂行为数据"},
            {
                "type": "choice",
                "question": f"关于「{topic}」的核心概念，下列说法最准确的是？",
                "options": ["仅强调机械记忆，无需理解", "理解核心概念并掌握基本方法", "与生活实践完全无关", "只需背诵结论即可"],
                "answer": 1,
            },
            {
                "type": "judge",
                "statements": [
                    {"text": f"「{topic}」的学习需要理解与运用相结合。", "answer": True},
                    {"text": f"学习「{topic}」与解决实际问题毫无关系。", "answer": False},
                    {"text": f"合作探究有助于深入理解「{topic}」。", "answer": True},
                ],
            },
            {
                "type": "drag",
                "prompt": f"请将「{topic}」的探究步骤拖到正确顺序：",
                "items": ["发现问题", "提出假设", "验证反思", "归纳结论"],
            },
            {"type": "fill", "question": f"请用一句话概括「{topic}」的核心要点：", "hint": "我的理解是……"},
            {"type": "summary", "points": ["练习完成，系统已采集你的课堂互动数据，用于后续教学优化"], "submit": True},
        ],
    }


def _render_slide(slide: dict, idx: int) -> str:
    t = (slide or {}).get("type")
    if t == "cover":
        return (
            f'<section class="slide active" data-slide="{idx}">'
            f'<div class="card cover"><span class="kicker">{_esc(slide.get("kicker", "教学演示"))}</span>'
            f'<h1>{_esc(slide.get("title", "交互式课件"))}</h1>'
            f'<p class="lead">{_esc(slide.get("subtitle", "分步讲解 · 数形结合 · 机理动画"))}</p></div></section>'
        )
    if t == "objectives":
        items = slide.get("items") or []
        body = "".join(
            f'<div class="obj"><b>目标 {i + 1}</b><span>{_esc(it)}</span></div>'
            for i, it in enumerate(items)
        )
        return f'<section class="slide" data-slide="{idx}"><div class="card"><h2>学习目标</h2>{body}</div></section>'
    if t == "content":
        heading = _esc(slide.get("heading", "核心知识"))
        cards = slide.get("cards") or []
        body = "".join(
            f'<div class="kcard" onclick="expand(this,\'content_{idx}_{i}\')"><b>{_esc(c.get("title", ""))}</b>'
            f'<div class="a">{_esc(c.get("body", ""))}</div></div>'
            for i, c in enumerate(cards)
        )
        return f'<section class="slide" data-slide="{idx}"><div class="card"><h2>{heading}</h2><div class="grid">{body}</div></div></section>'
    if t == "choice":
        opts = slide.get("options") or []
        ans = int(slide.get("answer", 0) or 0)
        letters = "ABCDEFGH"
        body = "".join(
            f'<div class="opt" data-q="choice_{idx}" data-answer="{"1" if i == ans else "0"}" onclick="choose(this)">'
            f'{letters[i] if i < len(letters) else i + 1}. {_esc(o)}</div>'
            for i, o in enumerate(opts)
        )
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>单选题</h2>'
            f'<p class="lead" style="margin-bottom:8px">{_esc(slide.get("question", ""))}</p>{body}'
            f'<div class="feedback" id="fb-choice_{idx}"></div></div></section>'
        )
    if t == "judge":
        stmts = slide.get("statements") or []
        rows = ""
        for j, s in enumerate(stmts):
            ans = "1" if s.get("answer", True) else "0"
            rows += (
                f'<div class="judge-row" data-q="judge_{idx}_{j}" data-answer="{ans}"><span>{_esc(s.get("text", ""))}</span>'
                f'<div><button class="btn" data-val="1" onclick="judge(this)">对</button>'
                f'<button class="btn" data-val="0" onclick="judge(this)">错</button></div></div>'
            )
        return f'<section class="slide" data-slide="{idx}"><div class="card"><h2>判断题</h2>{rows}</div></section>'
    if t == "drag":
        items = list(slide.get("items") or [])
        correct_order = "".join(str(i + 1) for i in range(len(items)))
        parts = []
        for i, it in enumerate(items):
            parts.append(
                f'<div class="drag-item" draggable="true" data-q="drag_{idx}" data-step="{i + 1}">{_esc(it)}</div>'
            )
        random.shuffle(parts)  # 打乱显示顺序，形成拖拽题
        rows_shuffled = "".join(parts)
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>拖拽排序</h2>'
            f'<p class="lead" style="margin-bottom:8px">{_esc(slide.get("prompt", ""))}</p>'
            f'<div class="drag-row" data-q="drag_{idx}" data-answer="{correct_order}">{rows_shuffled}</div>'
            f'<button class="btn primary" onclick="checkDrag(this.parentElement.querySelector(\'.drag-row\'))">检查顺序</button>'
            f'<div class="feedback" id="fb-drag_{idx}"></div></div></section>'
        )
    if t == "fill":
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>填空</h2>'
            f'<p class="lead" style="margin-bottom:8px">{_esc(slide.get("question", ""))}</p>'
            f'<input type="text" data-q="fill_{idx}" placeholder="{_esc(slide.get("hint", "我的理解是……"))}" onchange="checkFill(this)">'
            f'<div class="feedback" id="fb-fill_{idx}"></div></div></section>'
        )
    if t == "explore":
        poll = slide.get("poll") or []
        poll_html = "".join(
            f'<button class="opt" data-q="poll_{idx}" onclick="vote(this)">{_esc(p)}</button>' for p in poll
        )
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>探究任务</h2>'
            f'<p class="lead" style="margin-bottom:12px">{_esc(slide.get("question", ""))}</p>'
            f'<div class="poll">{poll_html}</div>'
            f'<textarea rows="2" placeholder="我还想探究……" onchange="track(\'explore_{idx}\',\'explore\',\'input\',this.value)"></textarea></div></section>'
        )
    if t == "match":
        pairs = slide.get("pairs") or []
        left_html = "".join(
            f'<div class="match-item left" data-q="match_{idx}" data-idx="{i}" onclick="matchPick(this)">{_esc(p.get("left", ""))}</div>'
            for i, p in enumerate(pairs)
        )
        order = list(range(len(pairs)))
        random.shuffle(order)
        right_html = "".join(
            f'<div class="match-item right" data-q="match_{idx}" data-idx="{j}" onclick="matchPick(this)">{_esc(pairs[j].get("right", ""))}</div>'
            for j in order
        )
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>连线匹配</h2>'
            f'<p class="lead" style="margin-bottom:12px">{_esc(slide.get("question", ""))}</p>'
            f'<div class="match-grid"><div class="match-col">{left_html}</div><div class="match-col">{right_html}</div></div>'
            f'<div class="feedback" id="fb-match_{idx}"></div></div></section>'
        )
    if t == "vote":
        poll = slide.get("options") or slide.get("poll") or []
        poll_html = "".join(
            f'<button class="opt" data-q="vote_{idx}" onclick="vote(this)">{_esc(p)}</button>' for p in poll
        )
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>投票</h2>'
            f'<p class="lead" style="margin-bottom:12px">{_esc(slide.get("question", ""))}</p>'
            f'<div class="poll">{poll_html}</div></div></section>'
        )
    if t == "steps":
        heading = _esc(slide.get("heading", "原理讲解"))
        steps = slide.get("steps") or []
        items = "".join(
            f'<div class="step" data-q="steps_{idx}"><b>{i + 1}. {_esc(s.get("title", ""))}</b>'
            f'<div class="step-body">{_esc(s.get("body", ""))}</div></div>'
            for i, s in enumerate(steps)
        )
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>{heading}</h2>'
            f'<div class="steps">{items}</div>'
            f'<button class="btn primary" style="margin-top:12px" onclick="nextStep(this)">下一步</button></div></section>'
        )
    if t == "graph":
        ftype = slide.get("function", "quadratic")
        heading = _esc(slide.get("heading", "函数图像"))
        note = _esc(slide.get("note", "拖动参数，观察图像变化"))
        if ftype == "linear":
            sliders = _slider(idx, "k", "斜率 k", -5, 5, 0.5, 1) + _slider(idx, "b", "截距 b", -5, 5, 0.5, 0)
        elif ftype == "sin":
            sliders = (
                _slider(idx, "A", "振幅 A", 0.5, 4, 0.5, 1)
                + _slider(idx, "w", "角频率 ω", 0.5, 4, 0.5, 1)
                + _slider(idx, "p", "相位 φ", 0, 6, 0.5, 0)
            )
        else:
            sliders = (
                _slider(idx, "a", "二次项 a", -3, 3, 0.1, 1)
                + _slider(idx, "b", "一次项 b", -5, 5, 0.5, 0)
                + _slider(idx, "c", "常数 c", -5, 5, 0.5, 0)
            )
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>{heading}</h2>'
            f'<p class="lead" style="margin-bottom:10px">{note}</p>'
            f'<canvas id="graph_{idx}" class="graph-canvas" data-fn="{ftype}" width="720" height="360"></canvas>'
            f'<div class="sliders">{sliders}</div></div></section>'
        )
    if t == "physics":
        heading = _esc(slide.get("heading", "抛体运动演示"))
        note = _esc(slide.get("note", "调整初速度和发射角，点击「发射」观察抛物线轨迹"))
        sliders = _slider(idx, "sp", "初速度 v", 10, 60, 2, 30) + _slider(idx, "an", "发射角 θ", 10, 80, 2, 45)
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card"><h2>{heading}</h2>'
            f'<p class="lead" style="margin-bottom:10px">{note}</p>'
            f'<canvas id="phys_{idx}" class="graph-canvas" width="720" height="340"></canvas>'
            f'<div class="sliders">{sliders}</div>'
            f'<div style="margin-top:12px"><button class="btn primary" onclick="launchProjectile({idx})">发射</button> '
            f'<button class="btn" onclick="resetProjectile({idx})">重置</button></div></div></section>'
        )
    if t == "summary":
        pts = slide.get("points") or []
        lis = "".join(f"<li style='text-align:left;margin:8px 0'>{_esc(p)}</li>" for p in pts)
        submit_html = ""
        if slide.get("submit"):
            submit_html = (
                '<p class="lead" id="summary"></p>'
                '<button class="btn primary" style="margin-top:20px" onclick="submitAll()">提交并生成学情反馈</button>'
            )
        return (
            f'<section class="slide" data-slide="{idx}"><div class="card" style="text-align:center;padding:48px 32px">'
            f'<h2 style="margin-bottom:16px">课堂小结</h2><ul style="list-style:none;max-width:480px;margin:0 auto 20px">{lis}</ul>'
            f'{submit_html}</div></section>'
        )
    return ""


def render_deck(deck: dict, cid: str) -> str:
    """把幻灯片内容（JSON）渲染成完整网页 PPT HTML。"""
    title = _esc(deck.get("title", "交互式课件"))
    slides = deck.get("slides") or []
    # 给封面注入课题标题（否则封面会显示默认的「交互式课件」）
    for s in slides:
        if s.get("type") == "cover" and not s.get("title"):
            s["title"] = deck.get("title", "交互式课件")
            break
    html_slides = []
    for i, s in enumerate(slides, 1):
        h = _render_slide(s, i)
        if h:
            html_slides.append(h)
    if not html_slides:
        return render_courseware(title, cid)
    has_interactive = any(s.get("type") in QUESTION_TYPES for s in slides)
    tracker = '<div class="tracker">📊 已采集 <b id="count">0</b> 次交互</div>' if has_interactive else ""
    return (
        DECK_HEAD.replace("__TITLE__", title)
        .replace("__SLIDES__", "\n".join(html_slides))
        .replace("__CID__", cid)
        .replace("__TRACKER__", tracker)
    )


def render_courseware(topic: str, cid: str) -> str:
    """渲染默认课件（Mock 模式）。"""
    return render_deck(build_default_deck(topic), cid)


def extract_html(text: str) -> str:
    """从模型输出中提取 HTML 代码。"""
    if not text:
        return ""
    m = re.search(r"```(?:html)?\s*(<!DOCTYPE[\s\S]*?</html>)\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"<!DOCTYPE[\s\S]*?</html>", text, re.IGNORECASE)
    if m:
        return m.group(0)
    m = re.search(r"<html[\s\S]*?</html>", text, re.IGNORECASE)
    if m:
        return m.group(0)
    return text
