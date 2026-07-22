# 阶段 2 · LLM 应用开发

目标：服务里能调大模型：输入"分析网络故障"，返回 LLM 的答案，并像 ChatGPT 一样逐字输出。

## 知识清单

### 大模型 API

- [x] OpenAI API 格式（messages 结构：system / user / assistant） → [llm-basics.md](llm-basics.md)
- [x] 调用 Qwen / DeepSeek（国内模型的 OpenAI 兼容接口） → [llm-basics.md](llm-basics.md)
- [x] API Key 管理（环境变量，不进 git） → [llm-basics.md](llm-basics.md)
- [x] 常用参数：temperature、max_tokens → [llm-basics.md](llm-basics.md)

### Prompt 工程

- [x] System Prompt 的作用（"你是一名通信网络专家……"） → [llm-basics.md](llm-basics.md)
- [x] 提示词单独存放管理（prompts/ 目录） → [llm-basics.md](llm-basics.md)
- [ ] 让 LLM 输出稳定 JSON 的技巧

### Streaming

- [x] 流式输出原理（SSE、chunk/delta、reasoning_content） → [llm-basics.md](llm-basics.md)
- [ ] FastAPI 里实现逐字返回
- [ ] 前端逐字渲染

> 已有基础：2025 年 3 月做过 Qwen / OpenAI 格式调用实验（wksp 下 Qwen.py、openaik.py），正式接入项目时回收沉淀。
