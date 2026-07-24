# 阶段 3 · RAG 知识库

目标：做一个通信知识库助手——网络规范 / 故障案例 / 设备手册入库，提问时先检索再回答。

管线：文档 → 解析 → 切分 → Embedding → 向量库 → 检索 → LLM 回答

## 知识清单

### 文档处理

- [x] Markdown 解析与按小节切分 → [rag-basics.md](rag-basics.md)
- [ ] PDF 解析（知识库接入 PDF 资料时）
- [x] 文本切分（chunk 粒度的权衡） → [rag-basics.md](rag-basics.md)

### Embedding 与向量库

- [x] Embedding 是什么（文本 → 向量，相近语义距离近） → [rag-basics.md](rag-basics.md)
- [x] Embedding API 调用（Qwen3-Embedding） → [rag-basics.md](rag-basics.md)
- [ ] BGE 中文 Embedding 模型（效果对比时）
- [ ] FAISS（轻量本地）
- [ ] Milvus（生产级向量库，文档规模化时）

### 检索与生成

- [x] 余弦相似度与 top-k 召回 → [rag-basics.md](rag-basics.md)
- [x] 检索结果进入对话的方式（工具化 RAG vs 固定管线） → [rag-basics.md](rag-basics.md)
- [x] 回答带出处引用 → [rag-basics.md](rag-basics.md)

> 已有基础：2025 年 3 月做过 noc_agent/rag/retrieval.py、Milvus 文档实验、sentence-transformers 本地 Embedding（all-MiniLM-L6-v2），正式接入项目时回收沉淀。
