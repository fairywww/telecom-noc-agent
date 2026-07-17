# 阶段 5 · 企业级 Agent 平台

目标：从"一个 Agent"到"一套平台"——多 Agent 协作、标准化工具接入、可量化的效果评测。

## 知识清单

### 多 Agent

- [ ] 总控 Agent + 子 Agent 架构（告警 Agent / 指标 Agent / 工单 Agent）
- [ ] Agent 间怎么传递任务与结果
- [ ] 什么时候该拆多 Agent，什么时候一个就够

### MCP（Model Context Protocol）

- [ ] MCP 是什么，解决什么问题（工具接入标准化）
- [ ] 写一个 MCP Server 暴露 NOC 工具
- [ ] MCP 与自定义 tool calling 的对比

### Agent 评测

- [ ] 成功率：怎么定义"这次诊断算对"
- [ ] 响应时间统计
- [ ] Token 消耗统计与成本核算
- [ ] 建一个小评测集回归测试
