"""Mock 学情数据：班级、学生、课堂交互、统计，用于演示教学闭环。

演示版本不接入真实校园数据库，全部使用模拟数据，规避联调 bug、保证稳定。
"""
import random


def get_class_info() -> dict:
    return {
        "class_name": "示例·初二(3)班",
        "subject": "示例学科",
        "teacher": "张老师",
        "student_count": 40,
    }


def get_students(n: int = 40) -> list:
    surnames = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨"
    given = ["子涵", "浩然", "欣怡", "梓萱", "明轩", "雨泽", "思颖", "天佑", "梦琪", "俊杰"]
    students = []
    for i in range(n):
        name = surnames[i % len(surnames)] + given[i % len(given)]
        students.append(
            {"id": f"stu_{i + 1:03d}", "name": name, "level": random.choice(["优秀", "良好", "待提升"])}
        )
    return students


def get_statistics() -> dict:
    """学情看板统计数据。"""
    return {
        "participation": {"avg": 87, "trend": [72, 75, 80, 78, 85, 87]},
        "accuracy": {"avg": 76, "trend": [65, 68, 70, 74, 73, 76]},
        "error_points": [
            {"name": "概念辨析", "value": 12},
            {"name": "方法应用", "value": 9},
            {"name": "综合迁移", "value": 6},
            {"name": "规范表达", "value": 4},
        ],
        "knowledge_mastery": [
            {"name": "基础知识", "value": 82},
            {"name": "方法技能", "value": 74},
            {"name": "综合应用", "value": 61},
        ],
    }


def get_interaction_records(n: int = 20) -> list:
    """模拟课堂交互记录。"""
    components = ["choice", "drag", "fill", "submit"]
    actions = ["select", "reorder", "input", "click"]
    values = ["A", "B", "C", "正确", "错误"]
    records = []
    for i in range(n):
        records.append(
            {
                "id": i + 1,
                "student": f"stu_{random.randint(1, 40):03d}",
                "component": random.choice(components),
                "action": random.choice(actions),
                "value": random.choice(values),
                "time": f"10:{random.randint(0, 59):02d}",
            }
        )
    return records


def simulate_learning_data(topic: str) -> dict:
    """模拟一节课的课堂交互学情数据（用于记忆回流演示）。"""
    return {
        "topic": topic,
        "class_name": "示例·初二(3)班",
        "total_interactions": 36,
        "accuracy": {"choice": 0.72, "drag": 0.68, "fill": 0.55},
        "wrong_records": [
            {"student": "stu_012", "knowledge_point": f"{topic}·概念辨析", "answer": "混淆了相似概念"},
            {"student": "stu_007", "knowledge_point": f"{topic}·方法应用", "answer": "步骤不完整"},
            {"student": "stu_023", "knowledge_point": f"{topic}·综合迁移", "answer": "未能迁移到新情境"},
        ],
    }


def build_learning_data(topic: str, aggregate: dict = None) -> dict:
    """优先使用真实课堂埋点聚合数据，否则回退模拟数据。"""
    if aggregate and aggregate.get("total_interactions", 0) > 0:
        return {
            "topic": topic,
            "class_name": "示例·初二(3)班",
            "total_interactions": aggregate["total_interactions"],
            "accuracy": aggregate.get("accuracy") or {},
            "wrong_records": aggregate.get("wrong_records") or [],
        }
    return simulate_learning_data(topic)
