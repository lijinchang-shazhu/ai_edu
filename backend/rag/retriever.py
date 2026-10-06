"""检索器：区分公共课标知识库与教师私有记忆库（私有库按教师隔离）。"""
import re

from backend.rag.vector_store import get_vector_store

PUBLIC = "public"  # 公共课标知识库（共享）
DEFAULT_TEACHER = "default"


def private_collection(teacher=None) -> str:
    """教师私有记忆库集合名（按教师隔离）。"""
    t = (teacher or DEFAULT_TEACHER).strip() or DEFAULT_TEACHER
    return "private_" + re.sub(r"[^0-9a-zA-Z_-]", "_", t)


PRIVATE = private_collection(DEFAULT_TEACHER)


def retrieve(query: str, collection: str = PRIVATE, k: int = 4) -> list:
    """在指定集合中检索相似内容。"""
    store = get_vector_store()
    return store.query(collection, query, k)


def retrieve_both(query: str, k_each: int = 3, teacher=None) -> dict:
    """同时检索公共课标知识库与指定教师的私有记忆库。"""
    store = get_vector_store()
    public = store.query(PUBLIC, query, k_each)
    private = store.query(private_collection(teacher), query, k_each)
    return {"public": public, "private": private}


def retrieve_doc(collection: str, doc_id: str, query_text: str, k: int = 6) -> list:
    """在指定集合内，仅针对某个文档（doc_id）的切片做相似检索。"""
    store = get_vector_store()
    return store.query_by_prefix(collection, query_text, doc_id, k)


def format_context(results: list) -> str:
    """将检索结果格式化为提示词可用的文本片段。"""
    if not results:
        return "（暂无历史相关记忆）"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}]（相关度 {r.get('score', '-')}）{r.get('text', '')}")
    return "\n".join(lines)
