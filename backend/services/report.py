"""学情薄弱点报告生成：整合课堂交互、易错点、记忆迭代记录。"""
from datetime import datetime

from backend.db.sqlite_db import db
from backend.services.mock_data import get_statistics


def build_report(topic: str = "示例课题") -> str:
    """生成 Markdown 格式的学情薄弱点报告。"""
    agg = db.aggregate_interactions()
    stats = get_statistics()
    memories = db.list_memories()

    lines = [f"# 学情薄弱点报告 · {topic}", ""]
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}（演示版本）")
    lines.append("")

    lines.append("## 一、课堂交互概况")
    lines.append(f"- 采集交互总数：{agg['total_interactions']} 次")
    if agg["accuracy"]:
        lines.append("- 各题型正确率：")
        for comp, acc in agg["accuracy"].items():
            lines.append(f"  - {comp}：{int(acc * 100)}%")
    else:
        lines.append("- 正确率：（暂无真实交互数据，以下为模拟统计）")
    lines.append("")

    lines.append("## 二、易错知识点分布")
    for e in stats["error_points"]:
        lines.append(f"- {e['name']}：{e['value']} 次")
    lines.append("")

    lines.append("## 三、记忆库迭代记录")
    if memories:
        for m in memories[:10]:
            lines.append(
                f"- 【{m['error_type']}】{m['knowledge_point']}：{m['suggestion']}（频次 {m['frequency']}）"
            )
    else:
        lines.append("- 暂无记忆条目")
    lines.append("")

    lines.append("## 四、教学改进建议")
    if memories:
        for m in memories[:5]:
            lines.append(f"- {m['suggestion']}")
    else:
        lines.append("- 建议针对高频易错点增加变式练习与正反例辨析")
        lines.append("- 落实「先理解、后应用」的规范步骤")
    return "\n".join(lines)
