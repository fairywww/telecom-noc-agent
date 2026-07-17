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
pip install -r requirements.txt

# 终端 1：启动模拟 NOC 后端
python3 -m uvicorn noc_backend:app --port 8001

# 终端 2：启动大屏后端（适配层 + 静态页面托管）
python3 -m uvicorn adapter:app --port 8002
```

浏览器打开 http://localhost:8002/ ，看到"全网退服总数 153 / 覆盖地市 3"即跑通。

## Roadmap

- [x] **v0.1 最小数据链路** — 三文件跑通 模拟NOC → 适配层 → 大屏
- [ ] **v0.2 多面板大屏** — 按运维"屏幕分区"心智增加指标面板（告警、退服、性能）
- [ ] **v0.3 接入真实数据源** — 适配层对接真实 NOC 接口，处理鉴权/异常/超时
- [ ] **v0.4 手写 Agent 循环** — 不用框架，手写 LLM 工具调用循环：查指标 → 分析 → 结论
- [ ] **v0.5 故障诊断 Agent** — Agent 自动完成「查数据 → 定位异常 → 生成诊断报告」
- [ ] **v0.6 RAG 通信知识库** — 网络规范/故障案例向量化，Agent 诊断时引用依据
- [ ] **v0.7 工程化** — Docker 一键启动、测试、日志、评测（成功率/耗时/Token）

## 知识库

[notes/](notes/) 是按六阶段路线组织的知识地图：每个阶段一份知识清单，学到一项勾一项，笔记只记本项目真实用到的、每条指到代码位置。

| 01 [Python+FastAPI](notes/01-python-fastapi/) | 02 [LLM应用](notes/02-llm-api/) | 03 [RAG](notes/03-rag/) | 04 [Agent](notes/04-agent/) | 05 [Agent平台](notes/05-agent-platform/) | 06 [通信Agent](notes/06-telecom-agent/) |
|---|---|---|---|---|---|

## 技术栈

当前：Python · FastAPI · 原生 HTML/JS
规划中：LLM 工具调用（手写循环）· Milvus/FAISS · BGE Embedding · Docker
