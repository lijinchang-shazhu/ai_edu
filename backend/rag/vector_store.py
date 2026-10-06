"""向量库管理。

优先使用 Chroma（轻量本地向量库）；若 Chroma 未安装或不可用，自动降级为
本地 JSON 向量存储。向量化支持两种模式：
- hash：本地哈希向量（离线可用、零依赖，默认）
- 在线 Embedding（openai/doubao/deepseek，配置 API Key 后启用）
"""
import hashlib
import json
import math
import threading
import uuid

from backend.config import settings


# ---------------------------------------------------------------------------
# 向量化
# ---------------------------------------------------------------------------
def hash_embed(text: str, dim: int = 384) -> list:
    """本地确定性向量：无需在线 Embedding 模型，离线可用。"""
    vec = [0.0] * dim
    text = (text or "").lower()
    tokens = list(text) + [text[i : i + 2] for i in range(len(text) - 1)]
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 10) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def embed_texts(texts, dim: int = 384) -> list:
    """批量向量化：配置真实 Embedding 时走在线模型，否则本地哈希。"""
    if settings.embedding_provider not in ("", "hash") and settings.llm_api_key:
        from backend.llm import get_llm

        try:
            vecs = get_llm().embed(texts)
            if vecs:
                return vecs
        except Exception:
            pass
    return [hash_embed(t, dim) for t in texts]


class LocalEmbeddingFunction:
    """适配 Chroma 的 Embedding Function 接口。"""

    def __call__(self, input):
        return embed_texts(input)


def _new_id() -> str:
    return uuid.uuid4().hex


class VectorStore:
    """统一向量存储接口。"""

    def __init__(self) -> None:
        self.backend = "chroma"
        self._client = None
        self._lock = threading.Lock()
        self._simple = self._load_simple()
        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=str(settings.chroma_dir))
            self._client.heartbeat()
        except Exception:
            self._client = None
            self.backend = "simple"

    # ---------- simple store 持久化 ----------
    def _load_simple(self) -> dict:
        if settings.vector_path.exists():
            try:
                return json.loads(settings.vector_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_simple(self) -> None:
        try:
            settings.vector_path.write_text(
                json.dumps(self._simple, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _fallback(self) -> None:
        self.backend = "simple"
        self._client = None

    # ---------- 公开接口 ----------
    def add_documents(self, collection: str, docs) -> int:
        """写入文档块。docs: [{id, text, metadata}]。返回写入数量。"""
        if not docs:
            return 0
        if self.backend == "chroma":
            try:
                col = self._client.get_or_create_collection(
                    name=collection, embedding_function=LocalEmbeddingFunction()
                )
                col.add(
                    ids=[d["id"] for d in docs],
                    documents=[d["text"] for d in docs],
                    metadatas=[d.get("metadata", {}) for d in docs],
                )
                return len(docs)
            except Exception:
                self._fallback()
        # simple 模式
        embs = embed_texts([d["text"] for d in docs])
        with self._lock:
            store = self._simple.setdefault(collection, [])
            for i, d in enumerate(docs):
                store.append(
                    {
                        "id": d["id"],
                        "text": d["text"],
                        "metadata": d.get("metadata", {}),
                        "embedding": embs[i],
                    }
                )
            self._save_simple()
        return len(docs)

    def query(self, collection: str, query_text: str, k: int = 4) -> list:
        """相似检索，返回 [{id, text, metadata, score}]，score 越大越相关。"""
        if self.backend == "chroma":
            try:
                col = self._client.get_or_create_collection(
                    name=collection, embedding_function=LocalEmbeddingFunction()
                )
                res = col.query(query_texts=[query_text], n_results=k)
                ids = (res.get("ids") or [[]])[0]
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                dists = (res.get("distances") or [[]])[0]
                out = []
                for i, did in enumerate(ids):
                    dist = dists[i] if i < len(dists) else 1.0
                    out.append(
                        {
                            "id": did,
                            "text": docs[i] if i < len(docs) else "",
                            "metadata": metas[i] if i < len(metas) else {},
                            "score": round(1.0 / (1.0 + float(dist)), 4),
                        }
                    )
                return out
            except Exception:
                self._fallback()
        # simple 模式
        store = self._simple.get(collection, [])
        qv = embed_texts([query_text])[0]
        scored = []
        for item in store:
            score = _cosine(qv, item.get("embedding", []))
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": it["id"],
                "text": it["text"],
                "metadata": it.get("metadata", {}),
                "score": round(sc, 4),
            }
            for sc, it in scored[:k]
        ]

    def query_by_prefix(self, collection: str, query_text: str, prefix: str, k: int = 6) -> list:
        """仅在与 prefix（doc_id）匹配的文档块中做相似检索。"""
        if self.backend == "chroma":
            try:
                col = self._client.get_or_create_collection(
                    name=collection, embedding_function=LocalEmbeddingFunction()
                )
                res = col.query(query_texts=[query_text], n_results=k, where={"doc_id": prefix})
                ids = (res.get("ids") or [[]])[0]
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                dists = (res.get("distances") or [[]])[0]
                out = []
                for i, did in enumerate(ids):
                    dist = dists[i] if i < len(dists) else 1.0
                    out.append(
                        {
                            "id": did,
                            "text": docs[i] if i < len(docs) else "",
                            "metadata": metas[i] if i < len(metas) else {},
                            "score": round(1.0 / (1.0 + float(dist)), 4),
                        }
                    )
                return out
            except Exception:
                self._fallback()
        # simple 模式
        store = self._simple.get(collection, [])
        qv = embed_texts([query_text])[0]
        scored = []
        for item in store:
            if item["id"].startswith(prefix + "-"):
                score = _cosine(qv, item.get("embedding", []))
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": it["id"],
                "text": it["text"],
                "metadata": it.get("metadata", {}),
                "score": round(sc, 4),
            }
            for sc, it in scored[:k]
        ]

    def delete(self, collection: str, ids) -> int:
        """删除文档块，返回删除数量。"""
        ids = list(ids) if not isinstance(ids, (list, tuple)) else ids
        if not ids:
            return 0
        if self.backend == "chroma":
            try:
                col = self._client.get_or_create_collection(
                    name=collection, embedding_function=LocalEmbeddingFunction()
                )
                col.delete(ids=list(ids))
                return len(ids)
            except Exception:
                self._fallback()
        with self._lock:
            store = self._simple.get(collection, [])
            id_set = set(ids)
            before = len(store)
            self._simple[collection] = [it for it in store if it["id"] not in id_set]
            removed = before - len(self._simple[collection])
            self._save_simple()
        return removed

    def list_ids(self, collection: str) -> list:
        """列出集合内所有文档块 id。"""
        if self.backend == "chroma":
            try:
                col = self._client.get_or_create_collection(
                    name=collection, embedding_function=LocalEmbeddingFunction()
                )
                return list(col.get()["ids"])
            except Exception:
                self._fallback()
        return [it["id"] for it in self._simple.get(collection, [])]

    def count(self, collection: str) -> int:
        if self.backend == "chroma":
            try:
                col = self._client.get_or_create_collection(
                    name=collection, embedding_function=LocalEmbeddingFunction()
                )
                return col.count()
            except Exception:
                self._fallback()
        return len(self._simple.get(collection, []))


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
