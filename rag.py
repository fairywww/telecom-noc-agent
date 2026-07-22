"""
文件5：RAG 知识检索 —— 给 Agent 一颗"查资料"的大脑
============================================================
管线：Markdown 文档 → 按小节切分 → Embedding 向量化（API）→ 内存索引 → 余弦检索

文档量小（几十个知识块）时不需要向量数据库：一个列表加余弦相似度就是
完整的 RAG 检索。FAISS/Milvus 解决的是"百万级向量还要快"的问题，
等文档规模上去再换，检索函数的对外接口不变。

用法：python3 rag.py "基站退服了应该怎么处置？"
"""
import os
import sys
import json
from pathlib import Path

from llm import 客户端

项目目录 = Path(__file__).parent
知识目录 = 项目目录 / "data" / "knowledge"
向量模型 = os.environ.get("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")


def 切分知识库():
    """把每个 md 文档按 ## 小节切成块。块是检索的最小单位：
    太大则一块混多个主题、检索不准；太小则上下文残缺、答非所问。"""
    块列表 = []
    for 文件 in sorted(知识目录.glob("*.md")):
        if 文件.name == "README.md":
            continue
        当前小节, 当前行 = "总述", []
        for 行 in 文件.read_text(encoding="utf-8").splitlines() + ["## <文档结束>"]:
            if 行.startswith("## "):
                正文 = "\n".join(当前行).strip()
                if 正文:
                    块列表.append({"来源": 文件.stem, "小节": 当前小节, "内容": 正文})
                当前小节, 当前行 = 行[3:].strip(), []
            else:
                当前行.append(行)
    return 块列表


def 向量化(文本列表):
    """文本 → 1024 维向量。语义相近的文本，向量方向也相近。"""
    应答 = 客户端.embeddings.create(model=向量模型, input=文本列表)
    return [条.embedding for 条 in 应答.data]


def 余弦相似度(甲, 乙):
    """两向量夹角的余弦：1 表示语义几乎相同，越小越不相关"""
    点积 = sum(x * y for x, y in zip(甲, 乙))
    模甲 = sum(x * x for x in 甲) ** 0.5
    模乙 = sum(y * y for y in 乙) ** 0.5
    return 点积 / (模甲 * 模乙)


_索引 = None    # [(块, 向量), ...]，首次检索时构建，之后常驻内存


def _建索引():
    global _索引
    块列表 = 切分知识库()
    # 参与向量化的文本带上来源和小节名——标题里的关键词对检索很有价值
    向量组 = 向量化([f"{块['来源']}·{块['小节']}\n{块['内容']}" for 块 in 块列表])
    _索引 = list(zip(块列表, 向量组))


def 检索(查询, top_k=3):
    """返回与查询语义最相近的 top_k 个知识块（含来源与相关度分值）"""
    global _索引
    if _索引 is None:
        _建索引()
    查询向量 = 向量化([查询])[0]
    打分 = sorted(
        ((余弦相似度(查询向量, 向量), 块) for 块, 向量 in _索引),
        key=lambda 项: -项[0],
    )
    return [
        {"来源": 块["来源"], "小节": 块["小节"], "内容": 块["内容"], "相关度": round(分, 3)}
        for 分, 块 in 打分[:top_k]
    ]


if __name__ == "__main__":
    查询 = sys.argv[1] if len(sys.argv) > 1 else "基站退服了应该怎么处置？"
    print(json.dumps(检索(查询), ensure_ascii=False, indent=2))
