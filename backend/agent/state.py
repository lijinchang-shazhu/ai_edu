"""Agent 状态定义：在多智能体之间传递信息的统一结构。"""
from typing import Any, Dict, List, Optional, TypedDict


class TeachingState(TypedDict, total=False):
    """教学流水线状态。

    字段说明：
    - doc_text / doc_title / subject / grade：输入材料与元信息
    - design：Agent1 解析出的教学设计（教学目标、重难点、知识点、学情）
    - memories：召回的历史记忆 {"public": [...], "private": [...]}
    - validation：Agent2 校验结果（课标匹配、问题、修改建议、final_design）
    - materials：Agent3 生成的全套素材（教案/习题/演讲稿/反思/微课脚本）
    - courseware_html：交互式网页课件 HTML 代码
    - learning_data：课堂 Mock 学情数据
    - memory_summary / memory_status：Agent4 记忆更新结果
    """

    # 输入
    doc_text: str
    doc_title: str
    subject: str
    grade: str

    # Agent1 输出
    design: Dict[str, Any]
    memories: Dict[str, List[dict]]

    # Agent2 输出
    validation: Dict[str, Any]

    # Agent3 输出
    materials: Dict[str, str]
    courseware_html: str

    # Agent4 输出
    learning_data: Dict[str, Any]
    memory_summary: Dict[str, Any]
    memory_status: str

    # 元信息
    error: Optional[str]
