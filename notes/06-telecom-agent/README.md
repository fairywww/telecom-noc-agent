# 阶段 6 · 通信行业 Agent（核心作品）

目标：整合前五个阶段的全部能力，形成最终作品——通信网络智能运维 Agent。

```
              用户
                |
        Agent Orchestrator
                |
   ------------------------------
   |            |               |
RAG 知识库    网络工具         数据分析
                |
              LLM
```

## 知识清单

### 场景能力

- [x] 故障诊断：指标输入 → 定位异常 → 诊断结论 → [../04-agent/tool-parameters.md](../04-agent/tool-parameters.md)
- [x] 智能问答：基于通信知识库的检索问答 → [../03-rag/rag-basics.md](../03-rag/rag-basics.md)
- [x] 自动生成工单：诊断结果 → 结构化工单（写操作三道防线） → [ticket-generation.md](ticket-generation.md)
- [x] 智能调度：告警事件 → 归并预筛 → Agent 研判 → 建议单人工确认 → 派单 → [dispatch.md](dispatch.md)
- [ ] 网络优化建议：基于数据分析给出建议

### 行业沉淀

- [ ] 通信运维术语与指标体系（退服、告警等级、专业划分）
- [ ] 运维人员的使用习惯怎么影响产品设计（屏幕分区心智）
- [ ] 真实 NOC 系统对接注意事项（鉴权、应答信封格式、数据口径）
