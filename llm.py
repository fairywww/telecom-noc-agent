"""
文件3：LLM 接入 —— 用 OpenAI 兼容格式调大模型
============================================================
所有主流大模型服务（ModelScope / 阿里 DashScope / DeepSeek 官方 / 本地
Ollama）都提供同一套 OpenAI 兼容接口：换 base_url 和模型名即可切换供应
商，代码一行不改。

密钥从 .env 文件读取（.env 已被 .gitignore 忽略，绝不进代码库）。

用法：python3 llm.py "全网退服 153 个、告警 477 条，严重吗？"
"""
import os
import sys
from pathlib import Path

from openai import OpenAI

项目目录 = Path(__file__).parent


def 加载环境文件():
    """把 .env 里的 KEY=VALUE 写入环境变量——密钥不进代码库的最简做法"""
    env文件 = 项目目录 / ".env"
    if env文件.exists():
        for 行 in env文件.read_text(encoding="utf-8").splitlines():
            行 = 行.strip()
            if 行 and not 行.startswith("#") and "=" in 行:
                键, 值 = 行.split("=", 1)
                os.environ.setdefault(键.strip(), 值.strip())


加载环境文件()

客户端 = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.environ["LLM_API_KEY"],   # 未配置会直接报 KeyError——密钥必须来自环境
)
模型名 = os.environ.get("LLM_MODEL", "deepseek-ai/DeepSeek-V4-Pro")
系统提示 = (项目目录 / "prompts" / "system.txt").read_text(encoding="utf-8")


def 问大模型(问题, 流式打印=False):
    """发一轮对话，返回最终答案文本。

    stream=True：应答按块（chunk）陆续到达，不必等全部生成完。
    推理模型会先输出思考过程（reasoning_content），再输出答案（content）；
    返回值只含答案，思考过程仅在流式打印时展示。
    """
    应答流 = 客户端.chat.completions.create(
        model=模型名,
        messages=[
            {"role": "system", "content": 系统提示},   # 角色与规则
            {"role": "user", "content": 问题},          # 本轮问题
        ],
        temperature=0.2,   # 运维问答要稳定可复现，随机性调低
        stream=True,
    )

    答案段 = []
    正在思考 = False
    for 块 in 应答流:
        if not 块.choices:
            continue
        增量 = 块.choices[0].delta
        思考文字 = getattr(增量, "reasoning_content", None) or ""
        答案文字 = 增量.content or ""
        if 思考文字 and 流式打印:
            print(思考文字, end="", flush=True)
            正在思考 = True
        if 答案文字:
            if 正在思考 and 流式打印:
                print("\n\n=== 结论 ===\n")
                正在思考 = False
            答案段.append(答案文字)
            if 流式打印:
                print(答案文字, end="", flush=True)
    if 流式打印:
        print()
    return "".join(答案段)


if __name__ == "__main__":
    问题 = sys.argv[1] if len(sys.argv) > 1 else "全网退服 153 个、告警 477 条，请评估严重程度。"
    问大模型(问题, 流式打印=True)
