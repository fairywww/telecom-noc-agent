"""
文件4：手写 Agent 循环 —— 本仓库的核心
============================================================
不用任何 Agent 框架。循环只有一条规则：

    LLM 推理 → 要求调工具? → 执行工具、结果回填对话历史 → 再推理
                └─ 不要求 → 它给出的就是最终答案，结束

工具就是 v0.2 做好的两个大屏接口。LLM 自己决定调哪个、调几次。

用法：python3 agent.py "现在网络状况怎么样？哪个地市最严重？"
（需要 8001/8002 两个服务在运行）
"""
import json
import sys

import requests

from llm import 客户端, 模型名, 项目目录

大屏后端 = "http://localhost:8002"


# ---------- 工具层：每个工具 = 一段说明 + 一个普通函数 ----------

def 查全网概览():
    return requests.get(f"{大屏后端}/api/kpi", timeout=5).json()


def 查地市退服明细():
    return requests.get(f"{大屏后端}/api/city-outage", timeout=5).json()


工具表 = {
    "查全网概览": {
        "函数": 查全网概览,
        "说明": "获取全网汇总指标：退服总数 outage_total、告警总数 alarm_total、覆盖地市数 city_count",
    },
    "查地市退服明细": {
        "函数": 查地市退服明细,
        "说明": "获取逐地市退服明细：各地市分专业(4G/5G)退服数与合计，已按严重程度降序排列",
    },
}


def 工具清单():
    """把工具表转成 OpenAI tools 格式——LLM 只凭 name 和 description 决定调谁"""
    return [
        {
            "type": "function",
            "function": {
                "name": 名,
                "description": 信息["说明"],
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
        for 名, 信息 in 工具表.items()
    ]


# ---------- 循环层 ----------

系统提示 = (项目目录 / "prompts" / "agent.txt").read_text(encoding="utf-8")


def 运行Agent(任务, 最大轮数=8):
    """Agent 的全部状态就是这份 messages 列表——每轮都完整重发"""
    messages = [
        {"role": "system", "content": 系统提示},
        {"role": "user", "content": 任务},
    ]

    for 轮 in range(1, 最大轮数 + 1):
        应答 = 客户端.chat.completions.create(
            model=模型名,
            messages=messages,
            tools=工具清单(),
            temperature=0.2,
        )
        消息 = 应答.choices[0].message

        # 终止条件①：模型不再要求调工具——它给出的就是最终答案
        if not 消息.tool_calls:
            print(f"\n=== 最终答案（第 {轮} 轮）===\n")
            print(消息.content)
            return 消息.content

        # 模型要求调工具：先把这条要求原样计入历史（含 tool_call_id，
        # 之后的 tool 消息靠这个 id 与要求一一对应）
        messages.append({
            "role": "assistant",
            "content": 消息.content,
            "tool_calls": [调用.model_dump() for 调用 in 消息.tool_calls],
        })

        for 调用 in 消息.tool_calls:
            名 = 调用.function.name
            print(f"[第 {轮} 轮] 模型调用工具：{名}")
            if 名 in 工具表:
                结果 = 工具表[名]["函数"]()
            else:
                结果 = {"error": f"未知工具：{名}"}    # 报错也回填，让模型自己纠正
            print(f"         工具返回：{json.dumps(结果, ensure_ascii=False)[:100]}")
            messages.append({
                "role": "tool",
                "tool_call_id": 调用.id,
                "content": json.dumps(结果, ensure_ascii=False),
            })

    # 终止条件②：轮数保护，防止模型陷入无限调用
    print(f"达到最大轮数 {最大轮数}，终止。")
    return None


if __name__ == "__main__":
    任务 = sys.argv[1] if len(sys.argv) > 1 else "现在全网状况如何？哪个地市最需要关注？给出诊断结论。"
    print(f"任务：{任务}\n")
    运行Agent(任务)
