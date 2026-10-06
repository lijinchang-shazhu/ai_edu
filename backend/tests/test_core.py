"""核心链路单元测试（离线、无需真实 API）。

运行：cd 项目根目录 && python -m pytest backend/tests -q
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# 强制离线 Mock 模式，保证单测不依赖网络/Key
os.environ["LLM_API_KEY"] = ""

from backend.agent.graph import run_pipeline
from backend.llm import _extract_tag, mock_chat, parse_json
from backend.rag.vector_store import _cosine, embed_texts, hash_embed


def test_parse_json_plain():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_with_code_fence():
    assert parse_json('```json\n{"b": 2}\n```') == {"b": 2}


def test_hash_embed_deterministic_and_similar():
    v1 = hash_embed("一元二次方程")
    v2 = hash_embed("一元二次方程")
    assert _cosine(v1, v2) > 0.99


def test_embed_texts_returns_list():
    vecs = embed_texts(["测试文本", "另一段"])
    assert len(vecs) == 2


def test_mock_chat_tag_extraction():
    msgs = [{"role": "system", "content": "任务标签: gen_lesson_plan\n..."}, {"role": "user", "content": "课题：示例"}]
    assert _extract_tag(msgs) == "gen_lesson_plan"
    out = mock_chat(msgs)
    assert "教案" in out


def test_run_pipeline_mock_full_loop():
    state = {
        "doc_text": "示例材料",
        "doc_title": "示例课题",
        "subject": "数学",
        "grade": "初二",
        "learning_data": {"topic": "示例课题", "total_interactions": 3},
    }
    r = run_pipeline(state)
    assert "design" in r and "validation" in r
    assert "lesson_plan" in r["materials"]
    assert "parent_letter" in r["materials"]
    assert len(r["courseware_html"]) > 1000
    assert "memory_status" in r
