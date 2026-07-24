"""OpenAI 兼容 LLM 客户端。

所有主流服务（ModelScope / DashScope / DeepSeek / 本地 Ollama）提供
同一套 OpenAI 兼容接口：切换供应商只改环境变量，代码零改动。

用法：python3 -m noc_agent.llm "你的问题"
"""
import os
import sys

from openai import OpenAI

from .config import prompt

client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.environ["LLM_API_KEY"],   # 未配置直接报错——密钥必须来自环境
)
MODEL = os.environ.get("LLM_MODEL", "Qwen/Qwen3.5-27B")


def ask(question, stream_print=False):
    """单轮对话，返回最终答案文本。

    推理模型会先流出思考过程（reasoning_content）再流出答案（content）；
    返回值只含答案，思考过程仅在流式打印时展示。
    """
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": prompt("system.txt")},
            {"role": "user", "content": question},
        ],
        temperature=0.2,   # 运维问答要求稳定可复现
        stream=True,
    )
    parts = []
    thinking = False
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None) or ""
        text = delta.content or ""
        if reasoning and stream_print:
            print(reasoning, end="", flush=True)
            thinking = True
        if text:
            if thinking and stream_print:
                print("\n\n=== 结论 ===\n")
                thinking = False
            parts.append(text)
            if stream_print:
                print(text, end="", flush=True)
    if stream_print:
        print()
    return "".join(parts)


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "全网退服 153 个、告警 477 条，请评估严重程度。"
    ask(question, stream_print=True)
