# 阶段 5 · 企业级 Agent 平台

目标：从"一个 Agent"到"一套平台"——多 Agent 协作、标准化工具接入、可量化的效果评测。

## 知识清单

### 多 Agent

- [x] 总控 Agent + 子 Agent 架构（Agent as Tool） → [multi-agent.md](multi-agent.md)
- [x] Agent 间怎么传递任务与结果（自包含子任务、来源标注、局限传递） → [multi-agent.md](multi-agent.md)
- [x] 什么时候该拆多 Agent（实测：2.6 倍词元、2.9 倍耗时的取舍） → [multi-agent.md](multi-agent.md)

### MCP（Model Context Protocol）

- [x] MCP 是什么，解决什么问题（M×N → M+N） → [mcp.md](mcp.md)
- [x] 写一个 MCP Server 暴露 NOC 工具（手写协议，stdio 传输） → [mcp.md](mcp.md)
- [x] MCP 与自定义 tool calling 的对比（同一份契约，两种信封） → [mcp.md](mcp.md)

### Agent 评测

- [x] 成功率：关键词判定与"这次诊断算对"的定义 → [agent-eval.md](agent-eval.md)
- [x] 响应时间统计 → [agent-eval.md](agent-eval.md)
- [x] Token 消耗统计（usage 累加、轮数与成本的关系） → [agent-eval.md](agent-eval.md)
- [x] 小评测集回归测试（已实际抓到并修复一个缺陷） → [agent-eval.md](agent-eval.md)
