"""FastAPI 入口：REST 接口，供 Vue 前端调用。

启动：uvicorn backend.main:app --host 0.0.0.0 --port 8000
"""
import json
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agent.agents import agent4_memory_update, tutor_chat
from backend.agent.graph import run_pipeline, run_pipeline_stream
from backend.config import settings
from backend.db.sqlite_db import db
from backend.rag.document_loader import classify_document, load_document_text, split_chunks
from backend.rag.retriever import private_collection
from backend.rag.vector_store import get_vector_store
from backend.services.material_gen import refine_courseware
from backend.services.mock_data import (
    build_learning_data,
    get_class_info,
    get_statistics,
    get_students,
)

TYPE_LABELS = {
    "lesson_plan": "教案",
    "exercises": "分层习题",
    "speech": "课堂演讲稿",
    "reflection": "教学反思",
    "micro_script": "微课脚本",
    "parent_letter": "家校沟通文案",
    "courseware": "讲课课件",
    "interactive": "随堂互动练习（采集学生学习状态）",
    "geometry_demo": "解析几何演示",
}

app = FastAPI(title="教师终身教学记忆 RAG 智能体系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------
class RunWorkflowRequest(BaseModel):
    doc_text: Optional[str] = None
    doc_id: Optional[str] = None
    doc_title: str = "示例课题"
    subject: str = "示例学科"
    grade: str = "示例年级"
    with_learning_data: bool = True
    teacher: str = "default"


class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = None
    session_id: Optional[str] = None
    teacher: str = "default"


class RefineRequest(BaseModel):
    instruction: str


class UpdateMaterialRequest(BaseModel):
    content: str


class SaveMaterialRequest(BaseModel):
    title: str
    content: str
    type: str = "note"


class LearningUpdateRequest(BaseModel):
    topic: str = "示例课题"
    teacher: str = "default"


class KbChatRequest(BaseModel):
    message: str
    doc_id: Optional[str] = None
    collection: Optional[str] = None
    history: Optional[list] = None
    teacher: str = "default"


# ---------------------------------------------------------------------------
# 基础
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"name": "教师终身教学记忆 RAG 智能体系统", "docs": "/docs", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return {
        "mode": "mock" if settings.mock_mode else settings.llm_provider,
        "mock_mode": settings.mock_mode,
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "vector_backend": get_vector_store().backend,
        "data_dir": str(settings.data_dir),
        "db_path": str(settings.db_path),
        "kb_docs": len(db.list_documents()),
        "materials": len(db.list_materials()),
        "memories": len(db.list_memories()),
    }


# ---------------------------------------------------------------------------
# 知识库管理
# ---------------------------------------------------------------------------
@app.post("/api/kb/upload")
async def kb_upload(
    file: UploadFile = File(...),
    collection: str = Form("private"),
    title: str = Form(""),
    teacher: str = Form("default"),
):
    """上传 PDF/Word 文档，解析、分块、向量化入库（collection 支持 auto 自动分类）。"""
    if collection not in ("public", "private", "auto"):
        raise HTTPException(status_code=400, detail="collection 必须为 public / private / auto")

    content = await file.read()
    filename = file.filename or "未命名文档"

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    save_path = settings.uploads_dir / f"{uuid.uuid4().hex}{Path(filename).suffix}"
    save_path.write_bytes(content)

    try:
        text = load_document_text(save_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"文档解析失败：{exc}")

    if not text:
        raise HTTPException(status_code=400, detail="未能从文档中解析出文本")

    if collection == "auto":
        collection = classify_document(text)
    actual = private_collection(teacher) if collection == "private" else "public"

    chunks = split_chunks(text)
    doc_id = db.add_document(title or filename, filename, actual, len(chunks), str(save_path))

    docs = [
        {
            "id": f"{doc_id}-{i}",
            "text": c,
            "metadata": {"title": title or filename, "collection": actual, "doc_id": doc_id},
        }
        for i, c in enumerate(chunks)
    ]
    get_vector_store().add_documents(actual, docs)

    return {
        "doc_id": doc_id,
        "title": title or filename,
        "collection": actual,
        "chunk_count": len(chunks),
    }


@app.get("/api/kb/list")
def kb_list(collection: Optional[str] = None, teacher: str = "default"):
    if collection == "private":
        return {"documents": db.list_documents(private_collection(teacher))}
    if collection == "public":
        return {"documents": db.list_documents("public")}
    if collection == "auto":
        return {"documents": []}
    # 全部：公共 + 当前教师私有
    return {"documents": db.list_documents("public") + db.list_documents(private_collection(teacher))}


@app.get("/api/kb/search")
def kb_search(q: str, collection: str = "private", k: int = 5, teacher: str = "default"):
    if collection == "private":
        collection = private_collection(teacher)
    results = get_vector_store().query(collection, q, k)
    return {"results": results}


@app.post("/api/kb/chat")
def kb_chat(req: KbChatRequest):
    """知识库文档问答：针对指定文档 / 分类做 RAG 增强提问。"""
    from backend.agent.agents import kb_question

    return kb_question(req.message, req.doc_id, req.collection, req.history, req.teacher)


@app.post("/api/kb/chat/stream")
def kb_chat_stream(req: KbChatRequest):
    """知识库文档问答（流式 SSE）。"""
    from backend.agent.agents import kb_question_stream

    def gen():
        for ev in kb_question_stream(req.message, req.doc_id, req.collection, req.history, req.teacher):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.delete("/api/kb/delete/{doc_id}")
def kb_delete(doc_id: str):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    collection = doc["collection"]
    ids = [i for i in get_vector_store().list_ids(collection) if i.startswith(f"{doc_id}-")]
    deleted = get_vector_store().delete(collection, ids)
    db.delete_document(doc_id)
    return {"deleted": deleted}


# ---------------------------------------------------------------------------
# Agent 工作流
# ---------------------------------------------------------------------------
def _build_state(req: RunWorkflowRequest):
    doc_text = req.doc_text or ""
    if req.doc_id and not doc_text:
        doc = db.get_document(req.doc_id)
        if doc and doc.get("path"):
            try:
                doc_text = load_document_text(doc["path"])
            except Exception:
                doc_text = ""
    title = req.doc_title or "示例课题"
    state = {
        "doc_text": doc_text,
        "doc_title": title,
        "subject": req.subject,
        "grade": req.grade,
        "teacher": req.teacher,
    }
    if req.with_learning_data:
        state["learning_data"] = build_learning_data(title, db.aggregate_interactions())
    return state, title


def _finalize(result: dict, title: str) -> dict:
    """持久化生成的素材并组装响应。"""
    materials = result.get("materials", {})
    material_items = {}
    for mtype, content in (materials or {}).items():
        label = TYPE_LABELS.get(mtype, mtype)
        mid = db.add_material(f"《{title}》{label}", mtype, content)
        material_items[mtype] = {"id": mid, "type": mtype, "label": label, "content": content}

    courseware_html = result.get("courseware_html", "")
    cid = db.add_material(
        f"《{title}》讲课课件",
        "courseware",
        courseware_html,
        meta={"deck": result.get("courseware_deck")},
    )

    return {
        "design": result.get("design", {}),
        "validation": result.get("validation", {}),
        "materials": material_items,
        "courseware": {"id": cid, "html": courseware_html},
        "memory": {
            "status": result.get("memory_status", ""),
            "summary": result.get("memory_summary", {}),
        },
        "mode": "mock" if settings.mock_mode else settings.llm_provider,
    }


@app.post("/api/workflow/run")
def workflow_run(req: RunWorkflowRequest):
    """触发多 Agent 流水线：解析 → 校验 → 生成 →（可选）记忆更新。"""
    state, title = _build_state(req)
    return _finalize(run_pipeline(state), title)


@app.post("/api/workflow/run/stream")
def workflow_run_stream(req: RunWorkflowRequest):
    """流式触发流水线，实时推送每个 Agent 的调用过程（SSE）。"""
    state, title = _build_state(req)

    def gen():
        for ev in run_pipeline_stream(state):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        resp = _finalize(state, title)
        yield f"data: {json.dumps({'type': 'done', 'result': resp}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# 随身师傅对话
# ---------------------------------------------------------------------------
@app.post("/api/chat")
def chat(req: ChatRequest):
    reply = tutor_chat(req.message, req.history, req.session_id, req.teacher)
    return {
        "reply": reply,
        "mode": "mock" if settings.mock_mode else settings.llm_provider,
    }


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """随身师傅流式对话（SSE）。"""
    from backend.agent.agents import tutor_messages
    from backend.llm import get_llm

    msgs = tutor_messages(req.message, req.history, req.session_id, req.teacher)

    def gen():
        for seg in get_llm().chat_stream(msgs):
            yield f"data: {json.dumps({'delta': seg}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# 学情数据
# ---------------------------------------------------------------------------
@app.get("/api/learning/class")
def learning_class():
    return get_class_info()


@app.get("/api/learning/students")
def learning_students():
    return {"students": get_students()}


@app.get("/api/learning/statistics")
def learning_statistics():
    return get_statistics()


@app.get("/api/learning/interactions")
def learning_interactions():
    """返回数据库中的课堂交互记录（启动时已填充演示数据）。"""
    return {"interactions": db.list_interactions(limit=50)}


@app.post("/api/learning/track")
def learning_track(req: dict = Body(default={})):
    """接收课件埋点上报的课堂交互行为（含题目 id、正确性、尝试次数）。"""
    db.add_interaction(
        req.get("coursewareId", ""),
        req.get("qid", ""),
        req.get("component", ""),
        req.get("action", ""),
        str(req.get("value", "")),
        req.get("correct"),
        req.get("attempt"),
        req.get("student", "mock_student_1"),
    )
    return {"ok": True}


@app.post("/api/learning/update")
def learning_update(req: LearningUpdateRequest):
    """触发学情记忆更新：提炼易错点并回流至教师私有记忆库。"""
    learning_data = build_learning_data(req.topic, db.aggregate_interactions())
    state = {"learning_data": learning_data, "doc_title": req.topic, "teacher": req.teacher}
    result = agent4_memory_update(state)
    return {
        "status": result.get("memory_status", ""),
        "summary": result.get("memory_summary", {}),
    }


@app.get("/api/learning/memories")
def learning_memories():
    return {"memories": db.list_memories()}


@app.get("/api/learning/report")
def learning_report(topic: str = "示例课题"):
    """生成学情薄弱点报告（Markdown）。"""
    from backend.services.report import build_report

    return {"report": build_report(topic), "topic": topic}


@app.get("/api/learning/report/download")
def learning_report_download(topic: str = "示例课题"):
    """下载学情薄弱点报告。"""
    from backend.services.report import build_report

    md = build_report(topic)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote('学情薄弱点报告.md')}"},
    )


# ---------------------------------------------------------------------------
# 素材管理
# ---------------------------------------------------------------------------
@app.get("/api/materials")
def list_materials():
    return {"materials": db.list_materials()}


@app.get("/api/materials/{mid}")
def get_material(mid: str):
    m = db.get_material(mid)
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    return m


@app.put("/api/materials/{mid}")
def update_material(mid: str, req: UpdateMaterialRequest):
    """在线编辑素材内容（自动保存历史版本）。"""
    m = db.get_material(mid)
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    db.update_material(mid, content=req.content)
    return {"ok": True, "id": mid}


@app.get("/api/materials/{mid}/versions")
def material_versions(mid: str):
    """素材版本历史。"""
    return {"versions": db.list_material_versions(mid)}


@app.post("/api/materials/save")
def save_material(req: SaveMaterialRequest):
    """保存问答内容为素材（「转为文档」）。"""
    mid = db.add_material(req.title, req.type, req.content)
    return {"id": mid, "title": req.title}


@app.post("/api/materials/{mid}/refine")
def refine_material(mid: str, req: RefineRequest):
    """课件自然语言微调（局部修改 HTML）。"""
    m = db.get_material(mid)
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    if m["type"] != "courseware":
        raise HTTPException(status_code=400, detail="仅支持对课件进行微调")
    new_html = refine_courseware(m["content"], req.instruction)
    db.update_material(mid, content=new_html)
    return {"id": mid, "html": new_html}


@app.delete("/api/materials/{mid}")
def delete_material(mid: str):
    db.delete_material(mid)
    return {"ok": True}


@app.get("/api/materials/{mid}/download")
def download_material(mid: str):
    m = db.get_material(mid)
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    if m["type"] in ("courseware", "interactive", "geometry_demo"):
        filename = f"{m['title']}.html"
        media_type = "text/html"
        content = m["content"]
    else:
        # 文本素材优先导出 Word(.docx)；缺 python-docx 时回退 .md
        try:
            from backend.services.doc_export import markdown_to_docx

            filename = f"{m['title']}.docx"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            content = markdown_to_docx(m["content"])
        except ImportError:
            filename = f"{m['title']}.md"
            media_type = "text/markdown"
            content = m["content"]

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@app.get("/api/courseware/{mid}")
def courseware_preview(mid: str):
    """交互式课件预览（供前端 iframe 嵌入）。"""
    m = db.get_material(mid)
    if not m:
        raise HTTPException(status_code=404, detail="课件不存在")
    return Response(content=m["content"], media_type="text/html")


@app.get("/api/edulab/problems")
def edulab_problems():
    """列出 edulab 可生成的解析几何题型。"""
    from backend.services.edulab_service import list_problems

    return {"problems": list_problems()}


@app.get("/api/edulab/generate/{key}")
def edulab_generate(key: str):
    """生成 edulab 解析几何交互演示网页。"""
    from backend.services.edulab_service import generate_geometry

    try:
        html = generate_geometry(key)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(content=html, media_type="text/html")


@app.get("/api/courseware/{mid}/export/pptx")
def courseware_export_pptx(mid: str):
    """导出课件为 .pptx（需安装 python-pptx）。"""
    m = db.get_material(mid)
    if not m:
        raise HTTPException(status_code=404, detail="课件不存在")
    deck = json.loads(m.get("meta") or "{}").get("deck")
    if not deck:
        raise HTTPException(status_code=400, detail="该课件缺少幻灯片数据，请重新生成")
    try:
        from backend.services.ppt_export import deck_to_pptx
    except ImportError:
        raise HTTPException(status_code=400, detail="未安装 python-pptx，请执行 pip install python-pptx 后重试")
    pptx_bytes = deck_to_pptx(deck)
    filename = f"{m['title']}.pptx"
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# 首次启动自动导入演示数据（幂等，失败不影响启动）
try:
    from backend.services.seed import seed_demo_data

    seed_demo_data()
except Exception:
    pass
