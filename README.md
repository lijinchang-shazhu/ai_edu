# 基于教师终身教学记忆 RAG 的新教师范式化育人智能体系统

面向教师群体，构建多智能体系统，沉淀教师个人教学记忆，辅助新教师备课、教研、课堂演练；
同源生成教案、习题、演讲稿、家校文案与交互式网页课件；支持课堂交互采集学情，学情数据回流
更新教师个人教学记忆，形成完整教学闭环。演示版本使用 Mock 学情数据。

> 本项目为 **代码自研方案**（Python + LangGraph），完全替代 Coze 零代码平台，工程自主可控。

---

## 一、核心特性

| 模块 | 说明 |
| --- | --- |
| 教师终身教学记忆 RAG | 上传 PDF/Word，自动解析、分块、向量化，区分「公共课标知识库」与「教师私有记忆库」 |
| 知识库文档问答 | 在知识库内选定文件 / 分类，基于 RAG 针对性提问，回答附带出处标注 |
| 多智能体流水线 | LangGraph 编排：教学解析 → 教学校验 → 素材生成 → 学情记忆更新 |
| AI 问答（随身师傅 + 文档问答） | 左侧知识库树 @ 引用文档/分类提问；复制/收藏/转为文档；情境模拟演练 |
| 同源素材生成 | 一键生成教案、分层习题、演讲稿、**家校文案**、教学反思、微课脚本、交互式网页课件 |
| 交互式网页课件（网页 PPT） | 多页幻灯片（封面/目标/讲解/单选/判断/拖拽/填空/探究/小结），翻页导航 + 深埋点 |
| 学情闭环 | 课件埋点采集 → 聚合 → 回流更新记忆库，课后自动生成**学情薄弱点报告** |
| AI 调用过程可视化 | 生成时实时滚动每个 Agent、每个素材的调用过程，直观展示大模型真实调用 |
| 教师档案 / 版本历史 | 教师身份切换；素材在线编辑自动记录历史版本 |
| 可视化教师工作台 | Vue3 + Tailwind + 线性 SVG 图标 + 动效，学情看板图表 + 报告可视化 |

---

## 二、技术架构

```
前端 Vue3 教师工作台  <--(http)-->  FastAPI 后端服务
                                        ↓
                              LangGraph 多 Agent 调度
                                        ↓
            ┌─────────────┬──────────────┴───────────────┬─────────────┐
       教学解析Agent   教学校验Agent   素材生成Agent    记忆更新Agent
            ↓             ↓                ↓                 ↓
        Chroma 向量库（教师私有记忆库 + 公共课标知识库）
            ↓
        SQLite 元数据 + 课堂交互埋点数据
```

- 后端：Python 3.10+ / FastAPI / LangGraph / LangChain / Chroma / SQLite
- 前端：Vue3 / Vite / Tailwind CSS / 线性 SVG 图标 / marked 渲染
- 大模型：OpenAI 兼容协议（DeepSeek / 豆包 / 通义千问 / OpenAI）

---

## 三、目录结构

```
he/
├── backend/                 # Python 后端
│   ├── main.py              # FastAPI 入口 + 路由
│   ├── config.py            # API KEY / 模型 / 路径配置
│   ├── llm.py               # 大模型客户端（含 Mock 降级 / 流式 / Embedding）
│   ├── smoke_test.py        # 冒烟测试（离线验证全链路）
│   ├── tests/               # pytest 单元测试
│   ├── requirements.txt     # 完整依赖
│   ├── .env.example         # 配置样例
│   ├── agent/               # state / prompts / agents / graph(LangGraph)
│   ├── rag/                 # document_loader / vector_store / retriever
│   ├── services/            # material_gen / courseware / mock_data / report / seed
│   └── db/                  # sqlite_db
├── frontend/                # Vue3 前端
│   └── src/                 # pages / components / api / router
├── demo_data/               # 演示样例文档（课标/教案/反思）
├── .env                     # 你的大模型 Key（已 gitignore）
├── start_backend.bat        # 一键启动后端
├── start_frontend.bat       # 一键启动前端
├── start_all.bat            # 一键启动前后端
└── README.md
```

---

## 四、快速开始

### 环境要求
- Python 3.10+
- Node.js 18+（npm）

### 方式一：一键启动（Windows）

```bat
双击 start_all.bat
```

将自动打开两个窗口：
- 后端：http://localhost:8000 （接口文档 http://localhost:8000/docs ）
- 前端：http://localhost:5173

> 首次启动会自动安装核心依赖（后端安装 fastapi/uvicorn，前端执行 npm install）。

### 方式二：手动启动

```bash
# 1. 后端
pip install -r backend/requirements.txt      # 完整依赖（可选）
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 2. 前端（新终端）
cd frontend
npm install
npm run dev
```

---

## 五、配置你的大模型 Key（.env）

在项目根目录的 `.env` 中填入你的 Key（以 DeepSeek 为例）：

```ini
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_MODEL=deepseek-chat
```

- **不填 Key** → 自动进入「演示模式（Mock）」，离线可用、零翻车。
- **填入 Key** → 自动切换为真实大模型智能生成；侧边栏底部徽标会从「演示模式」变为「真实大模型」。

> 若你使用的是豆包 / 通义 / 其他 OpenAI 兼容服务，改 `LLM_PROVIDER` 并填对应的
> `LLM_API_KEY`、`LLM_MODEL`（必要时填 `LLM_BASE_URL`）即可，无需改代码。

---

## 六、主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/kb/upload` | 上传 PDF/Word 文档入知识库 |
| GET | `/api/kb/list` | 文档列表 |
| GET | `/api/kb/search` | 知识库检索 |
| DELETE | `/api/kb/delete/{id}` | 删除文档 |
| POST | `/api/workflow/run` | 触发多 Agent 流水线，生成全套素材 |
| POST | `/api/chat` | 随身师傅对话（非流式） |
| POST | `/api/chat/stream` | 随身师傅对话（SSE 流式） |
| POST | `/api/learning/track` | 课件埋点上报（含题目 id / 正确性 / 尝试次数） |
| POST | `/api/learning/update` | 学情回流更新记忆库（聚合真实埋点） |
| GET | `/api/learning/report` | 生成学情薄弱点报告 |
| GET | `/api/learning/report/download` | 下载学情报告 |
| GET | `/api/materials` | 素材列表 |
| PUT | `/api/materials/{id}` | 在线编辑素材内容 |
| POST | `/api/materials/{id}/refine` | 课件自然语言微调 |
| GET | `/api/courseware/{id}` | 课件 HTML 预览（iframe 嵌入） |

---

## 七、演示流程建议（答辩）

1. **首页** → 展示系统定位、多智能体流水线、教学闭环。
2. **知识库** → 上传一份教案（可用 `demo_data/` 样例），展示自动向量化与双库隔离。
3. **教学素材** → 填写课题，一键生成，展示：
   - 教学解析 / 校验结果；
   - 六类素材（含家校文案）+ **多页交互式课件**（可翻页、点击、拖拽、填空）。
4. **学情看板** → 展示图表；点击「模拟学情回流」与「生成报告」，展示**学情薄弱点报告**。
5. **AI 问答** → 左侧点选文档/分类 @ 引用提问，或点击「情境演练」体验课堂控场/突发/家校模拟。

---

## 八、测试

```bash
# 冒烟测试（离线验证完整教学闭环）
python backend/smoke_test.py

# 单元测试
python -m pytest backend/tests -q
```

---

## 九、说明

- **网页 PPT 课件**：课件为多页幻灯片（9 页），内置翻页导航、进度条、键盘操作与深埋点
  （题目 id、正确性、尝试次数），真实课堂交互数据会回流后端并被报告聚合。
- **学情闭环**：`/api/learning/track` 采集的埋点会聚合后喂给记忆更新 Agent，不再依赖纯模拟数据。
- **Embedding**：默认本地哈希向量（离线可用）；配置 `EMBEDDING_PROVIDER=openai/doubao` + Key 后可切换在线 Embedding 提升召回精度。
- **AI 辅助定位**：所有生成内容仅供教学辅助，教师人工审核，不替代教师育人工作。
