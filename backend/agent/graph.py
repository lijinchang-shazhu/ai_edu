"""LangGraph 多 Agent 工作流编排（核心，替代 Coze 工作流）。

工作流：解析 → 校验 → 生成 →（有学情数据时）记忆更新 → 结束。
若 LangGraph 未安装或不可用，自动降级为顺序执行，功能不变，保证演示稳定。
"""
from backend.agent import agents
from backend.agent.state import TeachingState


def _node_parse(state):
    return agents.agent1_parse(state)


def _node_validate(state):
    return agents.agent2_validate(state)


def _node_generate(state):
    return agents.agent3_generate(state)


def _node_memory_update(state):
    return agents.agent4_memory_update(state)


def _route_after_generate(state):
    """条件边：收到学情数据时触发记忆更新分支。"""
    return "memory_update" if state.get("learning_data") else "end"


def _build_graph():
    from langgraph.graph import END, StateGraph

    g = StateGraph(TeachingState)
    g.add_node("parse", _node_parse)
    g.add_node("validate", _node_validate)
    g.add_node("generate", _node_generate)
    g.add_node("memory_update", _node_memory_update)

    g.set_entry_point("parse")
    g.add_edge("parse", "validate")
    g.add_edge("validate", "generate")
    g.add_conditional_edges(
        "generate",
        _route_after_generate,
        {"memory_update": "memory_update", "end": END},
    )
    g.add_edge("memory_update", END)
    return g.compile()


_graph = None


def get_graph():
    """返回编译好的 LangGraph；不可用时返回 False（降级标记）。"""
    global _graph
    if _graph is None:
        try:
            _graph = _build_graph()
        except Exception:
            _graph = False
    return _graph


def run_pipeline(state: dict) -> dict:
    """运行完整教学流水线，返回最终 state。"""
    g = get_graph()
    if g is False:
        # 降级：顺序调用，功能等价
        state.update(agents.agent1_parse(state))
        state.update(agents.agent2_validate(state))
        state.update(agents.agent3_generate(state))
        if state.get("learning_data"):
            state.update(agents.agent4_memory_update(state))
        return state
    return dict(g.invoke(state))


def run_pipeline_stream(state: dict):
    """运行流水线并逐步产出进度事件（供前端「AI 调用过程」可视化）。"""
    yield {"type": "step", "agent": "教学解析 Agent", "status": "running",
           "msg": "解析教材，检索教师个人教学记忆库…"}
    state.update(agents.agent1_parse(state))
    yield {"type": "step", "agent": "教学解析 Agent", "status": "done",
           "msg": "已提取教学目标、重难点与知识点"}

    yield {"type": "step", "agent": "教学校验 Agent", "status": "running",
           "msg": "对标新课标，校验知识点并过滤 AI 幻觉…"}
    state.update(agents.agent2_validate(state))
    yield {"type": "step", "agent": "教学校验 Agent", "status": "done",
           "msg": "校验完成，教学设计已修正"}

    state.update((yield from agents.agent3_generate_stream(state)))

    if state.get("learning_data"):
        yield {"type": "step", "agent": "记忆更新 Agent", "status": "running",
               "msg": "提炼课堂易错知识点，回流更新教师记忆库…"}
        state.update(agents.agent4_memory_update(state))
        yield {"type": "step", "agent": "记忆更新 Agent", "status": "done",
               "msg": state.get("memory_status", "记忆更新完成")}
