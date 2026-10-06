"""edulab 解析几何引擎封装（源码 Apache 2.0，来自 wy51ai/edulab）。

把一道解析几何题解成一个自包含的交互式教学网页：
三栏（题面 + 动态控制台滑块 + KaTeX 分步解析 + 2D Canvas 几何画板），
由 sympy 精确计算驱动（答案、坐标、步骤、交互引擎理论范围同源一致）。

复用方式：不调用「skill」，而是把 edulab 的 Python 计算核心内化为后端模块，
供「教学素材」生成数学课件时按需产出交互式解析几何演示页。
"""
import json
import sys
from pathlib import Path

_EDULAB_DIR = Path(__file__).resolve().parent.parent / "edulab" / "edu-analytic-geometry"
_SCRIPTS = _EDULAB_DIR / "scripts"
_TEMPLATE = _EDULAB_DIR / "template" / "board.html"


def _load_generate():
    """惰性加载 edulab 的 generate 模块（含 sympy，首次 import 稍慢）。"""
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    import generate  # noqa: F401  —— generate.py 内部会再挂 lib 并 import sympy

    return generate


def list_problems() -> list:
    """列出已注册的解析几何题型。"""
    return list(_load_generate().REGISTRY.keys())


def generate_geometry(problem_key: str) -> str:
    """按题型生成解析几何交互网页 HTML（字符串）。"""
    gen = _load_generate()
    if problem_key not in gen.REGISTRY:
        raise KeyError(f"未知题型 {problem_key}；可用: {', '.join(gen.REGISTRY)}")
    data = gen.REGISTRY[problem_key]()
    template = _TEMPLATE.read_text(encoding="utf-8")
    return template.replace("__LESSON_DATA__", json.dumps(data, ensure_ascii=False))
