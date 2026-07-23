# Telecom NOC Agent · 通信网络智能运维 Agent

一个从零手写、逐步生长的通信网络智能运维项目。
目标：不依赖框架黑盒，一步一步构建出「大屏 → 真数据 → Agent 循环 → RAG 知识库」的完整智能运维系统。

> 为什么是"通信 + Agent"：通用 AI 工程师很多，懂通信网络运维、又能手写 Agent 循环的人少。
> 这个仓库的提交历史本身就是一份"如何从零构建通信运维 Agent"的路线记录。

## 当前版本：v0.1 最小数据链路

三个文件，跑通一条最小但完整的数据链路：

```
noc_backend.py          adapter.py              index.html
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ 迷你 NOC 后端 │ HTTP │ 大屏后端      │ HTTP │ 大屏前端      │
│ (模拟生产系统) │─────▶│ (适配层:      │─────▶│ (取数→解析→   │
│ code/data 信封│      │  取数/加工/应答)│      │  展示,5秒刷新) │
└──────────────┘      └──────────────┘      └──────────────┘
     :8001                  :8002               浏览器
```

- **noc_backend.py** — 模拟生产环境已有的 NOC 系统：按地市/专业存数据，`{"code":0,"data":...}` 信封应答。真实场景中这个文件不存在，换成真实系统地址即可。
- **adapter.py** — 适配层，做三件事：调 NOC 接口取数 → 拆信封、聚合指标 → 按前后端契约输出字段。
- **index.html** — 大屏页面：fetch 取数 → JSON 解析 → 填入页面，每 5 秒刷新。

## 快速开始

```bash
# ① 克隆并创建隔离的 Python 环境
git clone https://github.com/fairywww/telecom-noc-agent.git
cd telecom-noc-agent
python3 -m venv .venv && source .venv/bin/activate

# ② 安装依赖（版本已锁定）
pip install -r requirements.txt

# ③ 配置大模型密钥（ModelScope 免费额度即可，https://modelscope.cn 获取）
cp .env.example .env    # 编辑 .env，填入你的 LLM_API_KEY

# ④ 启动两个服务（各占一个终端）
python3 -m uvicorn noc_backend:app --port 8001   # 模拟 NOC 数据源
python3 -m uvicorn adapter:app --port 8002       # 大屏后端 + Agent 接口
```

浏览器打开 http://localhost:8002/ ：左侧 KPI 与地市分布展示实时数据，右侧"智能诊断"面板可直接向 Agent 提问（如"哪个地市最需要关注？"）。

命令行方式使用 Agent 与知识检索：

```bash
python3 agent.py "南京退服全网最多，按规范该怎么处置？"
python3 rag.py "告警分几个等级？"
```

不配置密钥时，大屏数据展示（①②④）不受影响；仅 Agent 诊断功能需要 LLM。

装有 Docker 时可跳过 ①②④，一条命令启动全部服务：

```bash
docker compose up --build
```

开发自检：

```bash
python3 -m pytest tests/   # 单元测试（无网络依赖，秒级）
python3 eval.py            # Agent 评测集（成功率/轮数/耗时/Token）
```

## Roadmap

- [x] **v0.1 最小数据链路** — 三文件跑通 模拟NOC → 适配层 → 大屏
- [x] **v0.2 多面板大屏** — KPI、地市分布两面板接通真链路（故障等级、实时告警面板转入 backlog）
- [x] **v0.3 LLM 接入** — OpenAI 兼容格式调通 Qwen，system prompt 管理，密钥经 .env 注入
- [x] **v0.4 手写 Agent 循环** — 不用框架的工具调用循环：模型自主决定调 /api/kpi 或 /api/city-outage，基于真数据给诊断
- [x] **v0.5 故障诊断 Agent** — 带参数工具、错误自纠、Agent 服务化，大屏内嵌诊断对话窗（含工具调用轨迹展示）
- [x] **v0.6 RAG 通信知识库** — 知识文档切分 + Embedding + 余弦检索，作为 Agent 的知识工具，回答注明出处
- [x] **v0.7 工程化** — Docker compose 一键启动、pytest 测试套件、Agent 评测集（成功率/轮数/耗时/Token）
- [x] **v0.8 SSE 流式输出** — Agent 重构为单一流式生成器；工具轨迹实时推送、答案逐字渲染
- [x] **v0.9 MCP Server** — 工具层独立模块；手写最小 MCP 协议实现（initialize / tools/list / tools/call，stdio 传输）
- [x] **v1.0 多 Agent 协作** — 总控 + 数据分析/知识规范两专家（Agent as Tool），实测单/多 Agent 成本对比
- [ ] **backlog** — 大屏剩余面板（故障等级、实时告警）；适配层对接真实 NOC 数据源（鉴权/异常/超时）

## 知识库

[notes/](notes/) 是按六阶段路线组织的知识地图：每个阶段一份知识清单，学到一项勾一项，笔记只记本项目真实用到的、每条指到代码位置。

| 01 [Python+FastAPI](notes/01-python-fastapi/) | 02 [LLM应用](notes/02-llm-api/) | 03 [RAG](notes/03-rag/) | 04 [Agent](notes/04-agent/) | 05 [Agent平台](notes/05-agent-platform/) | 06 [通信Agent](notes/06-telecom-agent/) |
|---|---|---|---|---|---|

## 技术栈

当前：Python · FastAPI · 原生 HTML/JS · OpenAI 兼容 LLM API（Qwen）· 手写 Agent 循环（工具调用/多轮取数/轨迹展示）· RAG（Embedding + 余弦检索）· Docker · pytest · 评测集
当前还包括：MCP Server（手写协议实现）· 多 Agent 编排（总控 + 专家子 Agent）
规划中：Milvus/FAISS（知识规模化）· LangGraph 对比 · 多轮对话与 Memory
