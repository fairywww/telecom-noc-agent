# 阶段 4 · Agent 开发

目标：做出网络诊断 Agent——用户说"分析某区域网络异常"，Agent 自动查数据 → 分析 → 生成报告。

**本仓库的路线是先手写 Agent 循环，不依赖框架**；框架（LangGraph）安排在最后作对比学习。理由：能够完整讲清循环结构与每一步消息格式，比仅会调用框架接口更能证明理解深度。

## 知识清单

### 手写 Agent 循环（核心）

- [x] Agent 循环骨架：LLM 推理 → 决定调工具 → 执行 → 结果回填 → 再推理，直到给出答案 → [agent-loop.md](agent-loop.md)
- [x] Tool 定义：名称 / 描述 / 参数 schema，LLM 靠什么选工具 → [agent-loop.md](agent-loop.md)
- [x] tool calling 的完整消息结构（assistant 的 tool_calls、tool 角色消息） → [agent-loop.md](agent-loop.md)
- [x] 循环终止条件与最大轮数保护 → [agent-loop.md](agent-loop.md)
- [x] State：对话历史与中间结果怎么存 → [agent-loop.md](agent-loop.md)

### 框架对比（后置）

- [ ] LangChain 是什么，解决什么问题（了解即可）
- [ ] LangGraph：State / Node / Tool 概念，与手写版对照
- [ ] 同一个诊断 Agent 用 LangGraph 重写一遍，写对比笔记

> 已有基础：2025 年 3 月做过 tool calling 实验（weather.py、tools_test_note.py、agent.py），正式手写循环时回收沉淀。
