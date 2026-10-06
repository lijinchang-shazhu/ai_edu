"""四个核心 Agent：教学解析、教学校验、素材生成、学情记忆更新 + 随身师傅。"""
import uuid

from backend.agent import prompts
from backend.llm import get_llm
from backend.rag.retriever import PUBLIC, format_context, private_collection, retrieve, retrieve_both, retrieve_doc
from backend.services.material_gen import generate_all, generate_all_stream


def _context(memories: dict) -> str:
    """合并教师私有记忆与公共课标/名师经验为提示词上下文。"""
    return (
        "【教师个人教学记忆】\n"
        + format_context(memories.get("private", []))
        + "\n\n【公共课标知识库 / 名师经验】\n"
        + format_context(memories.get("public", []))
    )


def agent1_parse(state: dict) -> dict:
    """教学解析 Agent：解析上传材料 + 检索教师个人记忆与名师经验。"""
    doc_text = state.get("doc_text", "")
    title = state.get("doc_title", "示例课题")
    subject = state.get("subject", "示例学科")
    grade = state.get("grade", "示例年级")

    # 同时检索公共课标知识库 + 当前教师的私有记忆库
    memories = retrieve_both(f"{title} {subject} {grade}", k_each=3, teacher=state.get("teacher"))
    memories_text = _context(memories)

    design = get_llm().chat_json(
        prompts.parse_messages(doc_text, title, subject, grade, memories_text)
    )
    return {"design": design or {}, "memories": memories}


def agent2_validate(state: dict) -> dict:
    """教学校验 Agent：对标新课标、纠错、过滤 AI 幻觉。"""
    design = state.get("design", {})
    memories_text = _context(state.get("memories", {}))
    validation = get_llm().chat_json(prompts.validate_messages(design, memories_text))

    # 将校验后的 final_design 合并回 design（保留原课题标题），供后续生成使用
    merged = dict(design)
    if isinstance(validation, dict) and validation.get("final_design"):
        orig_title = merged.get("title")
        merged.update(validation["final_design"])
        if orig_title:
            merged["title"] = orig_title
    return {"validation": validation or {}, "design": merged}


def agent3_generate(state: dict) -> dict:
    """素材生成 Agent：分支生成教案/习题/演讲稿/反思/微课脚本/交互式课件。"""
    design = state.get("design", {})
    memories_text = _context(state.get("memories", {}))
    materials, courseware_html, deck = generate_all(design, memories_text)
    return {"materials": materials, "courseware_html": courseware_html, "courseware_deck": deck}


def agent3_generate_stream(state: dict):
    """素材生成 Agent（流式）：逐素材产出进度事件，最终返回状态更新。"""
    design = state.get("design", {})
    memories_text = _context(state.get("memories", {}))
    materials, courseware_html, deck = yield from generate_all_stream(design, memories_text)
    return {"materials": materials, "courseware_html": courseware_html, "courseware_deck": deck}


def agent4_memory_update(state: dict) -> dict:
    """学情记忆更新 Agent：提炼易错知识点并写入教师私有记忆库。"""
    from backend.db.sqlite_db import db
    from backend.rag.vector_store import get_vector_store

    learning_data = state.get("learning_data", {})
    summary = get_llm().chat_json(prompts.memory_extract_messages(learning_data))

    error_points = []
    if isinstance(summary, dict):
        error_points = summary.get("error_points", []) or []

    docs = []
    for ep in error_points:
        kp = ep.get("knowledge_point", "")
        etype = ep.get("error_type", "")
        suggestion = ep.get("suggestion", "")
        text = f"【易错点】{kp}｜类型：{etype}｜改进建议：{suggestion}"
        docs.append(
            {
                "id": f"mem-{uuid.uuid4().hex[:12]}",
                "text": text,
                "metadata": {"type": "error_point", "knowledge_point": kp},
            }
        )
        db.add_memory(kp, etype, suggestion, int(ep.get("frequency", 0) or 0))

    get_vector_store().add_documents(private_collection(state.get("teacher")), docs)

    return {
        "memory_summary": summary or {},
        "memory_status": f"已提炼 {len(error_points)} 个易错知识点并写入教师私有记忆库",
    }


_session_cache: dict = {}


def tutor_messages(message: str, history=None, session_id=None, teacher=None) -> list:
    """构建随身师傅对话消息（检索记忆 + 名师经验上下文，带会话缓存）。"""
    global _session_cache
    cache_key = f"{session_id}:{teacher}" if session_id else None
    if cache_key and cache_key in _session_cache:
        context_text = _session_cache[cache_key]
    else:
        memories = retrieve_both(message, k_each=2, teacher=teacher)
        context_text = _context(memories)
        if cache_key:
            if len(_session_cache) > 200:
                _session_cache.clear()
            _session_cache[cache_key] = context_text
    return prompts.tutor_messages(history or [], context_text, message)


def tutor_chat(message: str, history=None, session_id=None, teacher=None) -> str:
    """随身师傅：对话上下文绑定当前教师个人教学记忆。"""
    return get_llm().chat(tutor_messages(message, history, session_id, teacher))


def _kb_scope(message: str, doc_id=None, collection=None, teacher=None):
    """确定问答范围并检索，返回 (context_text, scope, sources)。"""
    from backend.db.sqlite_db import db

    if doc_id:
        doc = db.get_document(doc_id)
        if not doc:
            return None, "文档不存在或已被删除", []
        results = retrieve_doc(doc["collection"], doc_id, message, k=4)
        scope = f"文档《{doc['title']}》"
    elif collection == "public":
        results = retrieve(message, PUBLIC, k=4)
        scope = "公共课标知识库"
    elif collection == "private":
        results = retrieve(message, private_collection(teacher), k=4)
        scope = "教师私有记忆库"
    else:
        both = retrieve_both(message, k_each=3, teacher=teacher)
        results = both["private"] + both["public"]
        scope = "全部知识库"

    sources = [
        {"id": r["id"], "title": (r.get("metadata") or {}).get("title", ""), "text": r["text"][:120]}
        for r in results
    ]
    return format_context(results), scope, sources


def kb_qa_messages(message: str, doc_id=None, collection=None, teacher=None):
    """构建文档问答消息，返回 (messages, scope, sources)。无相关文档时保底通用回答。"""
    context_text, scope, sources = _kb_scope(message, doc_id, collection, teacher)
    if context_text is None:
        return None, scope, sources
    if not sources:
        # 无相关文档：直接用大模型通用回答，不拒绝
        msgs = [
            {"role": "system", "content": "你是一名专业、耐心的教育助手，请直接、实用地回答用户问题，用纯文本、自然段落表达，不要使用 Markdown 语法，绝不拒绝回答、绝不要求用户重新上传文档。"},
            {"role": "user", "content": message},
        ]
        return msgs, scope, sources
    return prompts.kb_qa_messages(context_text, message), scope, sources


def kb_question(message: str, doc_id=None, collection=None, history=None, teacher=None) -> dict:
    """知识库文档问答（非流式）。"""
    msgs, scope, sources = kb_qa_messages(message, doc_id, collection, teacher)
    if msgs is None:
        return {"reply": scope, "scope": scope, "sources": sources}
    reply = get_llm().chat(msgs)
    return {"reply": reply, "scope": scope, "sources": sources}


def kb_question_stream(message: str, doc_id=None, collection=None, history=None, teacher=None):
    """知识库文档问答（流式），产出 delta 与 done 事件。"""
    msgs, scope, sources = kb_qa_messages(message, doc_id, collection, teacher)
    if msgs is None:
        yield {"type": "delta", "delta": scope}
    else:
        for seg in get_llm().chat_stream(msgs):
            yield {"type": "delta", "delta": seg}
    yield {"type": "done", "scope": scope, "sources": sources}
