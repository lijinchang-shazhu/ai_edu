"""冒烟测试：在 Mock（离线）模式下验证完整教学闭环。

运行：python backend/smoke_test.py
不依赖真实 API Key / LangGraph / Chroma，全部走降级路径。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 强制离线 Mock 模式，保证冒烟测试不依赖网络/Key
os.environ["LLM_API_KEY"] = ""

# Windows 控制台默认 GBK，强制 UTF-8 输出避免中文/符号编码报错
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from backend.agent.graph import run_pipeline
from backend.config import settings


def main():
    print(f"模式: {'Mock 离线演示' if settings.mock_mode else settings.llm_provider}")
    state = {
        "doc_text": "本课为《示例课题》的教案材料，包含教学目标、重难点与课堂活动设计……",
        "doc_title": "示例课题",
        "subject": "示例学科",
        "grade": "示例年级",
        "learning_data": {
            "topic": "示例课题",
            "total_interactions": 36,
            "accuracy": {"choice": 0.72},
        },
    }
    result = run_pipeline(state)

    print("design keys       :", list(result.get("design", {}).keys()))
    print("validation keys   :", list(result.get("validation", {}).keys()))
    print("materials         :", list(result.get("materials", {}).keys()))
    print("courseware length :", len(result.get("courseware_html", "")))
    print("memory_status     :", result.get("memory_status", ""))
    print("SMOKE TEST PASSED ✅")


if __name__ == "__main__":
    main()
