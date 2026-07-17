# 阶段 3 · RAG 知识库

目标：做一个通信知识库助手——网络规范 / 故障案例 / 设备手册入库，提问时先检索再回答。

管线：文档 → 解析 → 切分 → Embedding → 向量库 → 检索 → LLM 回答

## 知识清单

### 文档处理

- [ ] PDF / Markdown 解析
- [ ] 文本切分（chunk 大小与重叠的权衡）

### Embedding 与向量库

- [ ] Embedding 是什么（文本 → 向量，相近语义距离近）
- [ ] BGE 中文 Embedding 模型
- [ ] FAISS（轻量本地）
- [ ] Milvus（生产级向量库）

### 检索与生成

- [ ] 相似度检索（top-k 召回）
- [ ] 检索结果拼进 Prompt 的方式
- [ ] 回答带出处引用

> 已有基础：2025 年 3 月做过 rag.py、Milvus 文档实验、sentence-transformers 本地 Embedding（all-MiniLM-L6-v2），正式接入项目时回收沉淀。
