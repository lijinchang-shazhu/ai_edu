"""演示数据自动导入（幂等）：首次启动时把 demo_data 样例写入知识库。

- 课标样例 → 公共课标知识库（public）
- 教案样例、教学反思样例 → 教师私有记忆库（private）
"""
import random

from backend.config import PROJECT_DIR
from backend.db.sqlite_db import db
from backend.rag.document_loader import split_chunks
from backend.rag.retriever import private_collection
from backend.rag.vector_store import get_vector_store

DEMO_FILES = [
    ("教案样例.md", "private"),
    ("教学反思样例.md", "private"),
    ("课标样例.md", "public"),
    ("名师经验-课堂管理.md", "public"),
    ("名师经验-家校沟通.md", "public"),
]

# 模拟课堂交互记录（题目编号 / 组件 / 操作 / 结果 / 是否正确）
INTERACTION_SAMPLES = [
    ("第1题", "choice", "select", "B. 理解核心概念并掌握方法", 1),
    ("第1题", "choice", "select", "A. 仅机械记忆", 0),
    ("第1题", "choice", "select", "C. 与生活实践无关", 0),
    ("第2题", "judge", "click", "对", 1),
    ("第2题", "judge", "click", "错", 0),
    ("第2题", "judge", "click", "对", 1),
    ("第3题", "drag", "check", "1234", 1),
    ("第3题", "drag", "check", "2134", 0),
    ("第3题", "drag", "check", "1243", 0),
    ("第4题", "fill", "submit", "理解核心概念与方法", 1),
    ("第4题", "fill", "submit", "不清楚", 0),
    ("第4题", "fill", "submit", "核心概念", 1),
    ("第5题", "match", "pair", "0-0", 1),
    ("第5题", "match", "pair", "0-2", 0),
    ("第5题", "match", "pair", "1-1", 1),
    ("第6题", "vote", "select", "影响很大", 1),
    ("第6题", "vote", "select", "一般", 1),
    ("第6题", "vote", "select", "没影响", 0),
]
_STUDENTS = ["stu_001", "stu_002", "stu_003", "stu_007", "stu_012", "stu_023", "stu_030", "stu_040"]


def seed_interactions(force: bool = False) -> int:
    """向数据库写入模拟课堂交互记录（仅当为空时）。"""
    if not force and db.list_interactions(limit=1):
        return 0
    n = 0
    for i, (qid, comp, action, value, correct) in enumerate(INTERACTION_SAMPLES):
        db.add_interaction("demo_courseware", qid, comp, action, value, correct, 1, _STUDENTS[i % len(_STUDENTS)])
        n += 1
    return n


SAMPLE_MATERIALS = [
    ("《一元二次方程》教案", "lesson_plan"),
    ("《一元二次方程》分层习题", "exercises"),
    ("《一元二次方程》课堂演讲稿", "speech"),
    ("《一元二次方程》教学反思", "reflection"),
    ("《一元二次方程》微课脚本", "micro_script"),
    ("《一元二次方程》家校文案", "parent_letter"),
]


def _sample_content(typ: str) -> str:
    if typ == "lesson_plan":
        return (
            "# 《一元二次方程》教案\n\n## 教学目标\n1. 知识与技能：掌握求根公式的推导与应用\n"
            "2. 过程与方法：通过配方法推导求根公式，经历从特殊到一般的探究过程\n\n"
            "## 教学重难点\n- 重点：求根公式及其应用\n- 难点：根的判别式的理解\n\n"
            "## 教学过程\n| 环节 | 教师活动 | 学生活动 |\n|---|---|---|\n| 情境导入 | 由实际问题引入 | 思考讨论 |\n| 合作探究 | 引导配方推导 | 动手推导 |\n"
        )
    if typ == "exercises":
        return (
            "# 《一元二次方程》分层练习\n\n## 基础巩固\n1. 解方程 x² - 5x + 6 = 0\n\n"
            "## 能力提升\n2. 用求根公式解 2x² + 3x - 2 = 0\n\n## 拓展探究\n3. 构造一个有两个实数根的一元二次方程\n"
        )
    if typ == "speech":
        return "# 《一元二次方程》课堂导入演讲稿\n\n同学们，生活中很多问题都能转化为方程……今天我们一起走进一元二次方程的世界。\n"
    if typ == "reflection":
        return "# 《一元二次方程》教学反思\n\n## 目标达成\n多数学生掌握了求根公式。\n\n## 不足\n部分学生符号处理不熟练。\n\n## 改进\n增加正反例辨析与变式练习。\n"
    if typ == "micro_script":
        return "# 《一元二次方程》微课脚本\n\n| 时间 | 画面 | 解说词 |\n|---|---|---|\n| 0:00-1:00 | 情境导入 | 由实际问题引入 |\n| 1:00-3:00 | 推导求根公式 | 配方法推导 |\n"
    return "# 《一元二次方程》家校文案\n\n尊敬的家长：\n\n近期我们学习了《一元二次方程》，建议引导孩子用生活中的实例理解方程，关注错题订正。\n"


def seed_materials(force: bool = False) -> int:
    """向数据库写入基础素材数据（仅当为空时）。"""
    if not force and db.list_materials():
        return 0
    from backend.services.courseware import build_default_deck, render_courseware

    n = 0
    for title, typ in SAMPLE_MATERIALS:
        db.add_material(title, typ, _sample_content(typ))
        n += 1
    html = render_courseware("一元二次方程", "seed_courseware")
    db.add_material("《一元二次方程》交互式课件", "courseware", html, meta={"deck": build_default_deck("一元二次方程")})
    return n + 1


def seed_demo_data(force: bool = False) -> dict:
    """导入演示数据，按文档标题判重（幂等）。"""
    store = get_vector_store()
    existing_titles = {d["title"] for d in db.list_documents()}

    demo_dir = PROJECT_DIR / "demo_data"
    seeded = 0
    for filename, collection in DEMO_FILES:
        path = demo_dir / filename
        if not path.exists():
            continue
        title = filename.replace(".md", "")
        if not force and title in existing_titles:
            continue
        actual = private_collection("default") if collection == "private" else "public"
        text = path.read_text(encoding="utf-8")
        chunks = split_chunks(text)
        doc_id = db.add_document(title, filename, actual, len(chunks), str(path))
        docs = [
            {
                "id": f"{doc_id}-{i}",
                "text": c,
                "metadata": {"title": title, "collection": actual, "doc_id": doc_id},
            }
            for i, c in enumerate(chunks)
        ]
        store.add_documents(actual, docs)
        seeded += 1
    int_count = seed_interactions(force)
    mat_count = seed_materials(force)
    return {"seeded": seeded, "interactions": int_count, "materials": mat_count}


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(seed_demo_data(force=True))
