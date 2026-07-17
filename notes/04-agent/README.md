# 阶段 4 · Agent 开发

目标：做出网络诊断 Agent——用户说"分析某区域网络异常"，Agent 自动查数据 → 分析 → 生成报告。

**本仓库路线：先手写 Agent 循环，不用框架。** 框架（LangGraph）放在最后做对比——面试时"我手写过循环、能讲清每一步消息结构"远比"我用过框架"值钱。

## 知识清单

### 手写 Agent 循环（核心）

- [ ] Agent 循环骨架：LLM 推理 → 决定调工具 → 执行 → 结果回填 → 再推理，直到给出答案
- [ ] Tool 定义：名称 / 描述 / 参数 schema，LLM 靠什么选工具
- [ ] tool calling 的完整消息结构（assistant 的 tool_calls、tool 角色消息）
- [ ] 循环终止条件与最大轮数保护
- [ ] State：对话历史与中间结果怎么存

### 框架对比（后置）

- [ ] LangChain 是什么，解决什么问题（了解即可）
- [ ] LangGraph：State / Node / Tool 概念，与手写版对照
- [ ] 同一个诊断 Agent 用 LangGraph 重写一遍，写对比笔记

> 已有基础：2025 年 3 月做过 tool calling 实验（weather.py、tools_test_note.py、agent.py），正式手写循环时回收沉淀。
