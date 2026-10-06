"""素材生成服务：同源生成教案 / 习题 / 演讲稿 / 反思 / 微课脚本 / 交互式网页课件。"""
import re
import time
import uuid

from backend.agent import prompts
from backend.llm import get_llm
from backend.services.courseware import build_default_deck, build_interactive_deck, render_deck, split_deck


def _cid() -> str:
    return uuid.uuid4().hex[:12]


MATERIAL_LABELS = {
    "lesson_plan": "教案",
    "exercises": "分层习题",
    "speech": "演讲稿",
    "reflection": "教学反思",
    "micro_script": "微课脚本",
    "parent_letter": "家校文案",
    "courseware": "讲课课件",
    "interactive": "随堂互动练习（采集学生学习状态）",
    "geometry_demo": "解析几何演示",
}

MATERIAL_BRANCHES = [
    ("lesson_plan", prompts.LESSON_PLAN_SYSTEM),
    ("exercises", prompts.EXERCISES_SYSTEM),
    ("speech", prompts.SPEECH_SYSTEM),
    ("reflection", prompts.REFLECTION_SYSTEM),
    ("micro_script", prompts.MICRO_SCRIPT_SYSTEM),
    ("parent_letter", prompts.PARENT_LETTER_SYSTEM),
]


def generate_all_stream(design, memories_text):
    """生成全套素材，逐步产出进度事件，最终返回 (materials, courseware_html, deck)。"""
    llm = get_llm()
    materials = {}
    for key, system in MATERIAL_BRANCHES:
        label = MATERIAL_LABELS[key]
        yield {"type": "step", "agent": "素材生成 Agent", "status": "running", "msg": f"正在生成{label}…"}
        t0 = time.time()
        materials[key] = llm.chat(prompts.gen_messages(system, design, memories_text))
        elapsed = time.time() - t0
        yield {"type": "step", "agent": "素材生成 Agent", "status": "done",
               "msg": f"{label}生成完成（{elapsed:.1f}s · {len(materials[key])} 字）"}

    yield {"type": "step", "agent": "素材生成 Agent", "status": "running", "msg": "正在生成教学课件（讲课 PPT）…"}
    cid = _cid()
    t0 = time.time()
    deck = llm.chat_json(prompts.courseware_messages(design, cid))
    if not isinstance(deck, dict) or not deck.get("slides"):
        deck = build_default_deck(design.get("title", "交互式课件"))
    # 强制拆分：教学页（讲课，无题目）+ 互动练习页（学情采集）
    teaching_slides, interactive_slides = split_deck(deck)
    if not teaching_slides:
        teaching_slides = build_default_deck(design.get("title", "本课"))["slides"]
    teaching_deck = dict(deck)
    teaching_deck["slides"] = teaching_slides
    html = render_deck(teaching_deck, cid)
    elapsed = time.time() - t0
    yield {"type": "step", "agent": "素材生成 Agent", "status": "done",
           "msg": f"教学课件生成完成（{elapsed:.1f}s · {len(teaching_slides)} 页）"}

    # 随堂互动练习（学情采集）：题目 + 埋点
    yield {"type": "step", "agent": "素材生成 Agent", "status": "running", "msg": "生成随堂互动练习（学情采集）…"}
    if interactive_slides:
        inter_deck = dict(deck)
        inter_deck["slides"] = interactive_slides
        materials["interactive"] = render_deck(inter_deck, _cid())
    else:
        materials["interactive"] = render_deck(build_interactive_deck(design.get("title", "本课")), _cid())
    yield {"type": "step", "agent": "素材生成 Agent", "status": "done", "msg": "随堂互动练习生成完成"}

    # 解析几何类课题：附加 edulab 交互演示（Apache 2.0 引擎）
    title = design.get("title") or ""
    geo_keywords = ["圆锥曲线", "椭圆", "双曲线", "抛物线", "解析几何"]
    if any(k in title for k in geo_keywords):
        yield {"type": "step", "agent": "素材生成 Agent", "status": "running", "msg": "生成解析几何交互演示（edulab 引擎）…"}
        try:
            from backend.services.edulab_service import generate_geometry

            materials["geometry_demo"] = generate_geometry("ellipse_dot_range")
        except Exception:
            pass
        yield {"type": "step", "agent": "素材生成 Agent", "status": "done", "msg": "解析几何交互演示生成完成"}

    return materials, html, deck


def generate_all(design, memories_text):
    """同源生成全套教学素材，返回 (materials, courseware_html, deck)。"""
    gen = generate_all_stream(design, memories_text)
    try:
        while True:
            next(gen)
    except StopIteration as exc:
        return exc.value


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


def _extract_cid(html: str) -> str:
    m = re.search(r'(?:coursewareId|CID)\s*=\s*["\']([^"\']+)["\']', html)
    if m:
        return m.group(1)
    return _cid()


def inject_tracking(html: str, cid: str) -> str:
    """确保课件 HTML 内嵌学情埋点脚本，并注入 courseware id。"""
    if not html:
        return html
    html = html.replace("__CID__", cid)
    if "api/learning/track" in html and "function track(" in html:
        # 已含埋点（如演示模板 / 真实模型已生成）
        return html

    script = (
        "<script>\n"
        f'  var CID = "{cid}";\n'
        "  var STUDENT = 'stu_' + Math.random().toString(36).slice(2, 6);\n"
        "  var _attempts = {};\n"
        "  function track(qid, component, action, value, extra) {\n"
        "    _attempts[qid] = (_attempts[qid] || 0) + 1;\n"
        "    var e = {coursewareId: CID, qid: qid, component: component, action: action, value: value, student: STUDENT, attempt: _attempts[qid]};\n"
        "    if (extra) { for (var k in extra) { e[k] = extra[k]; } }\n"
        "    try { fetch('/api/learning/track', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(e)}); } catch(err){}\n"
        "  }\n"
        "  document.addEventListener('click', function(e){ if(e.target.tagName === 'BUTTON'){ track('auto', 'click', 'click', (e.target.innerText || '').slice(0, 30)); } });\n"
        "</script>"
    )
    if "</body>" in html:
        return html.replace("</body>", script + "\n</body>")
    return html + script


def refine_courseware(current_html: str, instruction: str) -> str:
    """课件自然语言微调：局部修改 HTML，不重跑全流程。"""
    llm = get_llm()
    system = (
        "任务标签: refine_courseware\n"
        "你是一名前端开发专家，请根据修改要求，对现有交互式网页课件 HTML 进行局部修改。\n"
        "只输出修改后的完整 HTML 代码（用 ```html 包裹），不要任何解释。保留原有埋点脚本 track()。"
    )
    user = (
        f"现有课件 HTML：\n{current_html[:6000]}\n\n"
        f"修改要求：{instruction}\n\n请输出修改后的完整 HTML。"
    )
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    cid = _extract_cid(current_html)
    return inject_tracking(extract_html(llm.chat(msgs)), cid)
