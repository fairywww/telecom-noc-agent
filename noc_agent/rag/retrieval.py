"""RAG 知识检索。

管线：Markdown 文档 → 按小节切分 → Embedding 向量化（API）→ 内存索引 → 余弦检索

文档量小（几十个知识块）时不需要向量数据库：列表加余弦相似度就是
完整的检索。FAISS/Milvus 解决的是"百万级向量还要快"的问题，规模
上去时替换底层实现，search() 的对外接口不变。

用法：python3 -m noc_agent.rag.retrieval "基站退服了应该怎么处置？"
"""
import json
import os
import sys

from ..config import KNOWLEDGE_DIR
from ..llm import client

EMBED_MODEL = os.environ.get("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")


def load_chunks():
    """把每个 md 文档按 ## 小节切成块。块是检索的最小单位：
    太大则一块混多个主题、检索不准；太小则上下文残缺、答非所问。"""
    chunks = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        section, lines = "总述", []
        for line in path.read_text(encoding="utf-8").splitlines() + ["## <文档结束>"]:
            if line.startswith("## "):
                body = "\n".join(lines).strip()
                if body:
                    chunks.append({"source": path.stem, "section": section, "content": body})
                section, lines = line[3:].strip(), []
            else:
                lines.append(line)
    return chunks


def embed(texts):
    """文本 → 1024 维向量。语义相近的文本，向量方向也相近。"""
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in response.data]


def cosine_similarity(a, b):
    """两向量夹角的余弦：1 表示语义几乎相同，越小越不相关"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b)


_INDEX = None    # [(chunk, vector), ...]，首次检索时构建，之后常驻内存


def _build_index():
    global _INDEX
    chunks = load_chunks()
    # 参与向量化的文本带上来源和小节名——标题里的关键词对检索质量贡献很大
    vectors = embed([f"{c['source']}·{c['section']}\n{c['content']}" for c in chunks])
    _INDEX = list(zip(chunks, vectors))


def search(query, top_k=3):
    """返回与查询语义最相近的 top_k 个知识块（含来源与相关度分值）"""
    global _INDEX
    if _INDEX is None:
        _build_index()
    query_vector = embed([query])[0]
    ranked = sorted(
        ((cosine_similarity(query_vector, vector), chunk) for chunk, vector in _INDEX),
        key=lambda pair: -pair[0],
    )
    return [
        {"source": c["source"], "section": c["section"], "content": c["content"],
         "score": round(score, 3)}
        for score, c in ranked[:top_k]
    ]


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "基站退服了应该怎么处置？"
    print(json.dumps(search(query), ensure_ascii=False, indent=2))
