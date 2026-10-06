"""统一大模型客户端。

- 配置了真实 API Key 时：通过 OpenAI 兼容协议调用 DeepSeek / 豆包 / 通义千问 / OpenAI。
- 未配置时：降级为内置「演示模式（Mock）」，按任务标签返回结构化演示内容，
  保证离线、无 Key 的情况下全链路演示零翻车。
"""
import json
import re
import time
import urllib.request

from backend.config import settings


def _err_detail(exc) -> str:
    """从 HTTPError 中提取更可读的错误信息。"""
    try:
        if hasattr(exc, "read"):
            return exc.read().decode("utf-8", "ignore")[:200]
    except Exception:
        pass
    return str(exc)


class LLMClient:
    """大模型客户端（OpenAI 兼容协议，纯标准库实现，零依赖）。"""

    def __init__(self) -> None:
        self._ready = settings.llm_available

    @property
    def available(self) -> bool:
        return self._ready

    def _post(self, path: str, payload: dict):
        url = settings.base_url.rstrip("/") + path
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.llm_api_key}",
            },
            method="POST",
        )
        return urllib.request.urlopen(req, timeout=settings.llm_timeout)

    def chat(self, messages, temperature=None, max_tokens=None) -> str:
        """对话补全，返回纯文本（失败自动重试）。"""
        if not self._ready:
            return mock_chat(messages)
        last_err = None
        for attempt in range(3):
            try:
                resp = self._post(
                    "/chat/completions",
                    {
                        "model": settings.llm_model,
                        "messages": messages,
                        "temperature": settings.llm_temperature if temperature is None else temperature,
                        "max_tokens": max_tokens or settings.llm_max_tokens,
                    },
                )
                body = json.loads(resp.read().decode("utf-8"))
                return (body["choices"][0]["message"]["content"] or "").strip()
            except Exception as exc:  # 重试，最后才降级
                last_err = exc
                time.sleep(1.0 * (attempt + 1))
        return mock_chat(messages, note=f"[大模型调用失败，返回示例内容：{_err_detail(last_err)}]")

    def chat_json(self, messages, temperature=0.3):
        """对话补全并解析为 JSON（dict / list）。"""
        text = self.chat(messages, temperature=temperature)
        return parse_json(text)

    def embed(self, texts):
        """文本向量化（OpenAI 兼容协议），失败重试后返回 None。"""
        if not self._ready:
            return None
        for attempt in range(2):
            try:
                resp = self._post("/embeddings", {"model": settings.embedding_model, "input": texts})
                body = json.loads(resp.read().decode("utf-8"))
                return [d["embedding"] for d in body["data"]]
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        return None

    def chat_stream(self, messages, temperature=None):
        """流式对话，逐段产出文本（生成器）。"""
        if not self._ready:
            text = mock_chat(messages)
            for i in range(0, len(text), 24):
                yield text[i : i + 24]
            return
        try:
            payload = {
                "model": settings.llm_model,
                "messages": messages,
                "temperature": settings.llm_temperature if temperature is None else temperature,
                "max_tokens": settings.llm_max_tokens,
                "stream": True,
            }
            url = settings.base_url.rstrip("/") + "/chat/completions"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.llm_api_key}",
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=settings.llm_timeout)
            for raw in resp:
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    j = json.loads(chunk)
                    delta = (j.get("choices") or [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield delta
                except Exception:
                    continue
        except Exception as exc:
            for seg in mock_chat(messages, note=f"[大模型调用失败：{_err_detail(exc)}]").split():
                yield seg + " "


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    """获取全局单例 LLM 客户端。"""
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm


# --------------------------------------------------------------------------
# JSON 解析工具
# --------------------------------------------------------------------------
def parse_json(text: str):
    """从模型输出中稳健提取 JSON。"""
    if not text:
        return {}
    text = text.strip()
    text = re.sub(r"^```(json|JSON)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        s = text.find(opener)
        if s != -1:
            e = text.rfind(closer)
            if e > s:
                try:
                    return json.loads(text[s : e + 1])
                except Exception:
                    continue
    return {}


# --------------------------------------------------------------------------
# 演示模式（Mock）
# --------------------------------------------------------------------------
def _extract_topic(messages) -> str:
    """从消息中提取课题/主题，用于演示内容占位。"""
    blob = "\n".join(str(m.get("content", "")) for m in messages)
    for pat in (
        r"课题[:：]\s*([^\n]+)",
        r"标题[:：]\s*([^\n]+)",
        r"主题[:：]\s*([^\n]+)",
        r"教学内容[:：]\s*([^\n]+)",
        r"题目[:：]\s*([^\n]+)",
    ):
        m = re.search(pat, blob)
        if m:
            topic = m.group(1).strip().strip("《》\"'“”")
            if topic:
                return topic
    return "示例课题"


def _extract_tag(messages) -> str:
    """提取任务标签（约定：提示词以「任务标签: xxx」开头）。"""
    blob = "\n".join(str(m.get("content", "")) for m in messages)
    m = re.search(r"任务标签[:：]\s*([A-Za-z_]+)", blob)
    return m.group(1) if m else ""


def _last_user(messages) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return ""


# ---------- 各任务标签的演示内容生成器 ----------
def _mock_parse_teaching(topic):
    return json.dumps(
        {
            "title": topic,
            "subject": "示例学科",
            "grade": "示例年级",
            "objectives": {
                "知识与技能": f"理解并掌握「{topic}」的核心概念与基本方法",
                "过程与方法": f"通过自主探究与合作学习，经历「{topic}」的生成过程，发展学科核心素养",
                "情感态度价值观": f"激发对「{topic}」的学习兴趣，培养严谨求实的科学态度",
            },
            "key_points": [f"{topic}的核心概念", "关键方法/公式的推导与应用"],
            "difficult_points": [f"{topic}的易错点与易混淆概念", "综合情境下的迁移应用"],
            "knowledge_points": [f"{topic}·基础知识", f"{topic}·方法技能", f"{topic}·综合应用"],
            "student_profile": "学生具备一定基础，但对抽象概念理解薄弱，需通过直观情境与分层练习巩固",
        },
        ensure_ascii=False,
        indent=2,
    )


def _mock_validate_teaching(topic):
    return json.dumps(
        {
            "is_valid": True,
            "standard_match": "符合新课标对核心素养的要求，目标设计体现知识、能力、素养三层结构",
            "issues": ["重难点表述可更聚焦学生真实易错点", "建议增加评价量规，使目标可测量"],
            "corrections": [
                "将「理解概念」细化为可观察的行为动词（如「能举例说明 / 能正确计算」）",
                "补充分层练习与课堂提问设计，落实「教—学—评」一致",
            ],
            "final_design": {
                "title": topic,
                "objectives": f"围绕「{topic}」形成可测量的三维教学目标",
                "key_points": f"{topic}核心概念与方法",
                "difficult_points": f"{topic}易错点与迁移应用",
                "suggested_activities": ["情境导入", "合作探究", "分层练习", "反思小结"],
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def _mock_lesson_plan(topic):
    return f"""# 《{topic}》教案

## 一、教学目标
1. 知识与技能：理解并掌握「{topic}」的核心概念与基本方法。
2. 过程与方法：通过探究与合作，经历知识生成过程，发展学科核心素养。
3. 情感态度价值观：激发学习兴趣，培养严谨求实的科学态度。

## 二、教学重难点
- 重点：{topic}的核心概念与方法。
- 难点：{topic}的易错点与综合迁移应用。

## 三、教学过程
| 环节 | 教师活动 | 学生活动 | 设计意图 |
| --- | --- | --- | --- |
| 情境导入(5min) | 创设生活情境，引出{topic} | 观察、思考、提出疑问 | 激发兴趣、明确问题 |
| 合作探究(20min) | 组织小组探究，引导归纳 | 动手操作、小组讨论 | 突破难点、建构概念 |
| 精讲点拨(10min) | 精讲核心方法，示范规范 | 记录要点、模仿演练 | 落实重点、规范表达 |
| 分层练习(8min) | 布置基础/提升/拓展题 | 独立完成、互评 | 分层巩固、及时反馈 |
| 反思小结(2min) | 引导总结、布置作业 | 梳理知识、自我评价 | 形成结构、延伸学习 |

## 四、板书设计（略）
## 五、教学反思
（课后填写：记录学生易错点，回流至个人教学记忆库）
"""


def _mock_exercises(topic):
    return f"""# 《{topic}》分层随堂练习

## 基础巩固（全员达标）
1. 【选择】关于「{topic}」的基本概念，下列说法正确的是（  ）
   A. 选项一  B. 选项二  C. 选项三  D. 选项四
2. 【填空】{topic}的核心方法是 ______，它用于解决 ______ 类问题。

## 能力提升（学有余力）
3. 【简答】请用自己的话说明「{topic}」在生活中的一个应用，并分析其原理。
4. 【辨析】判断下列说法的对错，并说明理由。

## 拓展探究（挑战思维）
5. 【开放】结合「{topic}」，设计一个探究小问题链，并写出你的研究思路。
"""


def _mock_speech(topic):
    return f"""# 《{topic}》课堂导入演讲稿

同学们好！今天上课之前，老师先给大家讲一个小情境……

（结合生活实例，自然引出「{topic}」）

那么，这背后到底藏着怎样的规律呢？带着这个问题，我们一起走进今天的内容——《{topic}》。

好，请同学们打开课本，先观察老师出示的几组例子，想一想它们有什么共同点……
"""


def _mock_reflection(topic):
    return f"""# 《{topic}》教学反思

## 一、教学目标达成情况
本课围绕「{topic}」设计探究活动，多数学生能够理解核心概念，教学目标基本达成。

## 二、亮点
- 情境导入贴近生活，学生参与度高。
- 分层练习兼顾不同层次学生，课堂反馈及时。

## 三、不足与改进
- 部分学生对「{topic}」的易错点仍存在混淆，后续需增加变式练习。
- 小组合作时间分配可再优化。

## 四、学生易错点记录（回流至个人记忆库）
- 易错点1：概念辨析不清
- 易错点2：方法应用不规范
"""


def _mock_micro_script(topic):
    return f"""# 《{topic}》微课脚本（3~5 分钟）

| 时间 | 画面 | 解说词 |
| --- | --- | --- |
| 0:00-0:20 | 片头+课题 | 大家好，欢迎来到微课堂，今天我们一起学习《{topic}》。 |
| 0:20-1:30 | 情境导入 | 先看一个生活中的例子……引出核心问题。 |
| 1:30-3:00 | 知识讲解 | 讲解「{topic}」的核心概念与方法，配合动画演示。 |
| 3:00-4:00 | 例题示范 | 通过典型例题，示范规范解题步骤。 |
| 4:00-4:30 | 小结作业 | 回顾要点，布置分层练习。 |
"""


def _mock_parent_letter(topic):
    return f"""# 《{topic}》家校沟通文案

尊敬的各位家长：

您好！近期我们在课堂上学习了「{topic}」，为了让您更好地了解孩子的学习情况，特与您沟通如下：

## 一、本阶段学习重点
{topic}的核心概念与基本方法是本阶段重点，重在理解与运用相结合。

## 二、孩子可能遇到的困难
- 对抽象概念的理解不够深入，容易出现机械记忆；
- 从知识到实际运用的迁移能力有待加强。

## 三、家校配合建议
1. 引导孩子用生活中的实例理解「{topic}」，多问「为什么」；
2. 鼓励孩子用自己的话复述所学内容，检验是否真正理解；
3. 关注孩子的学习习惯，避免单纯刷题、忽视理解。

感谢您的支持与配合！如孩子在学习中遇到困难，欢迎随时与我沟通。

（示例文案，供教师参考修改）
"""


def _mock_courseware(topic, cid):
    from backend.services.courseware import render_courseware

    return render_courseware(topic, cid)


def _mock_tutor_chat(topic, user_msg):
    return (
        f"作为经验丰富的带教师傅，针对你的问题，我的建议如下：\n\n"
        f"1. 明确目标：围绕「{topic or '本节课'}」先定清教学目标与重难点，再组织活动。\n"
        f"2. 以生为本：多设计学生参与度高的小组活动与分层练习，避免「满堂灌」。\n"
        f"3. 家校沟通：与家长沟通时，先说孩子亮点，再客观描述现象，最后给可操作建议。\n"
        f"4. 突发处置：保持冷静、先稳情绪、再处理问题，课后及时复盘记录。\n\n"
        f"如需更具体的建议，请告诉我你的学科、年级和具体场景，我再为你细化。"
    )


def _mock_kb_qa(topic):
    return (
        "根据知识库中检索到的文档内容，为你梳理如下要点：\n"
        "1. 文档中明确了相关概念的核心定义与要点；\n"
        "2. 建议结合文档中的案例与规范步骤进行理解与迁移。"
    )


def _mock_memory_extract(topic):
    return json.dumps(
        {
            "error_points": [
                {
                    "knowledge_point": f"{topic}·概念辨析",
                    "error_type": "概念混淆",
                    "frequency": 12,
                    "suggestion": "增加正反例对比与变式练习",
                },
                {
                    "knowledge_point": f"{topic}·方法应用",
                    "error_type": "步骤不规范",
                    "frequency": 9,
                    "suggestion": "示范规范步骤，强调易错细节",
                },
                {
                    "knowledge_point": f"{topic}·综合迁移",
                    "error_type": "情境迁移困难",
                    "frequency": 6,
                    "suggestion": "设计真实情境，引导迁移应用",
                },
            ],
            "summary": f"本节课「{topic}」学生主要易错点集中在概念辨析与方法应用上，建议下节课针对性强化。",
        },
        ensure_ascii=False,
        indent=2,
    )


def _mock_refine_courseware(user_msg):
    """离线模式下课件微调：返回原有 HTML（演示为无操作，需真实 Key 才可微调）。"""
    m = re.search(r"<!DOCTYPE[\s\S]*?</html>", user_msg, re.IGNORECASE) or re.search(
        r"<html[\s\S]*?</html>", user_msg, re.IGNORECASE
    )
    return m.group(0) if m else user_msg


_TAG_HANDLERS = {
    "parse_teaching": _mock_parse_teaching,
    "validate_teaching": _mock_validate_teaching,
    "gen_lesson_plan": _mock_lesson_plan,
    "gen_exercises": _mock_exercises,
    "gen_speech": _mock_speech,
    "gen_reflection": _mock_reflection,
    "gen_micro_script": _mock_micro_script,
    "gen_parent_letter": _mock_parent_letter,
    "memory_extract": _mock_memory_extract,
    "kb_qa": _mock_kb_qa,
}


def mock_chat(messages, note: str = "") -> str:
    """离线演示：按任务标签返回结构化演示内容。"""
    tag = _extract_tag(messages)
    topic = _extract_topic(messages)
    user_msg = _last_user(messages)

    if tag == "gen_courseware_html":
        cid = re.search(
            r"课件ID[:：]\s*([A-Za-z0-9]+)",
            "\n".join(str(m.get("content", "")) for m in messages),
        )
        cid = cid.group(1) if cid else "demo_courseware"
        result = _mock_courseware(topic, cid)
    elif tag == "tutor_chat":
        result = _mock_tutor_chat(topic, user_msg)
    elif tag == "refine_courseware":
        result = _mock_refine_courseware(user_msg)
    elif tag in _TAG_HANDLERS:
        result = _TAG_HANDLERS[tag](topic)
    else:
        result = f"关于「{topic}」，这是一段示例内容（大模型未接入时显示）。"

    if note:
        result = note + "\n\n" + result
    return result
