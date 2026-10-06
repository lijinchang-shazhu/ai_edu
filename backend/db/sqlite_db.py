"""SQLite 元数据存储：文档、素材、学情埋点、记忆更新日志。

演示版本使用轻量本地 SQLite，无需额外数据库服务。
"""
import json
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from backend.config import settings


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_id() -> str:
    return uuid.uuid4().hex


_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents(
    id TEXT PRIMARY KEY,
    title TEXT,
    filename TEXT,
    collection TEXT,
    chunk_count INTEGER DEFAULT 0,
    path TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS materials(
    id TEXT PRIMARY KEY,
    title TEXT,
    type TEXT,
    content TEXT,
    meta TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS interactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    courseware_id TEXT,
    qid TEXT,
    component TEXT,
    action TEXT,
    value TEXT,
    correct INTEGER,
    attempt INTEGER,
    student TEXT,
    meta TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS memories(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_point TEXT,
    error_type TEXT,
    suggestion TEXT,
    frequency INTEGER,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS material_versions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id TEXT,
    content TEXT,
    created_at TEXT
);
"""

_db_path: Path | None = None


def _resolve_db_path() -> Path:
    """解析数据库路径：优先主数据目录，失败退回系统临时目录（仅解析一次，保证一致）。"""
    global _db_path
    if _db_path is not None:
        return _db_path
    candidates = [settings.db_path, Path(tempfile.gettempdir()) / "teacher_ai_system" / "app.db"]
    for p in candidates:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(p))
            conn.execute("BEGIN")
            conn.execute("CREATE TABLE _ping(id INTEGER)")
            conn.execute("ROLLBACK")
            conn.close()
            _db_path = p
            return p
        except Exception:
            continue
    _db_path = settings.db_path
    return _db_path


def _ensure_schema(conn) -> None:
    """幂等建表 + 列迁移（每次连接都执行，自愈）。"""
    conn.executescript(_SCHEMA)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(interactions)").fetchall()}
    for name, typ in (("qid", "TEXT"), ("correct", "INTEGER"), ("attempt", "INTEGER"), ("meta", "TEXT")):
        if name not in cols:
            conn.execute(f"ALTER TABLE interactions ADD COLUMN {name} {typ}")


@contextmanager
def _db():
    """打开数据库连接：每次连接前确保目录存在并保证表结构完整（自愈）。"""
    p = _resolve_db_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
    except Exception:
        global _db_path
        _db_path = Path(tempfile.gettempdir()) / "teacher_ai_system" / "app.db"
        _db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_db_path))
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


class Database:
    """应用数据库访问层。"""

    def __init__(self) -> None:
        self.init()

    def init(self) -> None:
        with _db():
            pass  # 初始化时即确保表结构存在

    # ---------- 文档 ----------
    def add_document(self, title, filename, collection, chunk_count, path) -> str:
        doc_id = _new_id()
        with _db() as c:
            c.execute(
                "INSERT INTO documents(id,title,filename,collection,chunk_count,path,created_at)"
                " VALUES(?,?,?,?,?,?,?)",
                (doc_id, title, filename, collection, chunk_count, path, _now()),
            )
        return doc_id

    def list_documents(self, collection=None):
        with _db() as c:
            if collection:
                rows = c.execute(
                    "SELECT * FROM documents WHERE collection=? ORDER BY created_at DESC",
                    (collection,),
                ).fetchall()
            else:
                rows = c.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get_document(self, doc_id):
        with _db() as c:
            r = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        return dict(r) if r else None

    def delete_document(self, doc_id) -> None:
        with _db() as c:
            c.execute("DELETE FROM documents WHERE id=?", (doc_id,))

    # ---------- 素材 ----------
    def add_material(self, title, type_, content, meta=None) -> str:
        mid = _new_id()
        with _db() as c:
            c.execute(
                "INSERT INTO materials(id,title,type,content,meta,created_at)"
                " VALUES(?,?,?,?,?,?)",
                (mid, title, type_, content, json.dumps(meta or {}, ensure_ascii=False), _now()),
            )
        return mid

    def list_materials(self):
        with _db() as c:
            rows = c.execute(
                "SELECT id,title,type,meta,created_at FROM materials ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_material(self, mid):
        with _db() as c:
            r = c.execute("SELECT * FROM materials WHERE id=?", (mid,)).fetchone()
        return dict(r) if r else None

    def update_material(self, mid, content=None, title=None) -> None:
        with _db() as c:
            if content is not None:
                old = c.execute("SELECT content FROM materials WHERE id=?", (mid,)).fetchone()
                if old:
                    c.execute(
                        "INSERT INTO material_versions(material_id, content, created_at) VALUES(?,?,?)",
                        (mid, old["content"], _now()),
                    )
                c.execute("UPDATE materials SET content=? WHERE id=?", (content, mid))
            if title is not None:
                c.execute("UPDATE materials SET title=? WHERE id=?", (title, mid))

    def list_material_versions(self, mid):
        with _db() as c:
            rows = c.execute(
                "SELECT id, content, created_at FROM material_versions WHERE material_id=? ORDER BY id DESC",
                (mid,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_material(self, mid) -> None:
        with _db() as c:
            c.execute("DELETE FROM materials WHERE id=?", (mid,))

    # ---------- 学情埋点 ----------
    def add_interaction(self, courseware_id, qid, component, action, value, correct, attempt, student, meta=None) -> None:
        with _db() as c:
            c.execute(
                "INSERT INTO interactions(courseware_id,qid,component,action,value,correct,attempt,student,meta,created_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (courseware_id, qid, component, action, value, correct, attempt, student, meta, _now()),
            )

    def list_interactions(self, limit=200):
        with _db() as c:
            rows = c.execute(
                "SELECT * FROM interactions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def interaction_stats(self):
        with _db() as c:
            total = c.execute("SELECT COUNT(*) AS n FROM interactions").fetchone()["n"]
            by_component = c.execute(
                "SELECT component, COUNT(*) AS n FROM interactions GROUP BY component"
            ).fetchall()
        return {"total": total, "by_component": [dict(r) for r in by_component]}

    def aggregate_interactions(self) -> dict:
        """聚合课堂埋点数据为学情统计（供记忆更新与学情报告使用）。"""
        with _db() as c:
            rows = [dict(r) for r in c.execute("SELECT * FROM interactions ORDER BY id").fetchall()]
        by_component = {}
        for r in rows:
            comp = r["component"] or "other"
            d = by_component.setdefault(comp, {"total": 0, "correct": 0})
            d["total"] += 1
            if r["correct"] == 1:
                d["correct"] += 1
        accuracy = {
            comp: round(d["correct"] / d["total"], 2) if d["total"] else 0.0
            for comp, d in by_component.items()
        }
        wrong_records = [
            {
                "qid": r["qid"] or "",
                "student": r["student"] or "",
                "component": r["component"] or "",
                "value": r["value"] or "",
            }
            for r in rows
            if r["correct"] == 0
        ][:50]
        return {
            "total_interactions": len(rows),
            "accuracy": accuracy,
            "wrong_records": wrong_records,
            "by_component": [
                {"component": k, "total": v["total"], "correct": v["correct"]}
                for k, v in by_component.items()
            ],
        }

    # ---------- 记忆更新日志 ----------
    def add_memory(self, knowledge_point, error_type, suggestion, frequency) -> None:
        with _db() as c:
            c.execute(
                "INSERT INTO memories(knowledge_point,error_type,suggestion,frequency,created_at)"
                " VALUES(?,?,?,?,?)",
                (knowledge_point, error_type, suggestion, frequency, _now()),
            )

    def list_memories(self):
        with _db() as c:
            rows = c.execute("SELECT * FROM memories ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


db = Database()
