"""
文件4：手写 Agent 循环 —— 本仓库的核心
============================================================
不用任何 Agent 框架。循环只有一条规则：

    LLM 推理 → 要求调工具? → 执行工具、结果回填对话历史 → 再推理
                └─ 不要求 → 它给出的就是最终答案，结束

工具就是大屏适配层的接口。LLM 自己决定调哪个、传什么参数、调几次。

用法：python3 agent.py "苏州的情况怎么样？"
（需要 8001/8002 两个服务在运行）
"""
import json
import sys

import requests

from llm import 客户端, 模型名, 项目目录

大屏后端 = "http://localhost:8002"


# ---------- 工具层：每个工具 = 一段说明 + 一份参数说明 + 一个普通函数 ----------

def 查全网概览():
    return requests.get(f"{大屏后端}/api/kpi", timeout=5).json()


def 查地市退服明细():
    return requests.get(f"{大屏后端}/api/city-outage", timeout=5).json()


def 查指定地市明细(city):
    return requests.get(f"{大屏后端}/api/city-detail", params={"city": city}, timeout=5).json()


无参数 = {"type": "object", "properties": {}, "required": []}

工具表 = {
    "查全网概览": {
        "函数": 查全网概览,
        "参数": 无参数,
        "说明": "获取全网汇总指标：退服总数 outage_total、告警总数 alarm_total、覆盖地市数 city_count",
    },
    "查地市退服明细": {
        "函数": 查地市退服明细,
        "参数": 无参数,
        "说明": "获取逐地市退服明细：各地市分专业(4G/5G)退服数与合计，已按严重程度降序排列",
    },
    "查指定地市明细": {
        "函数": 查指定地市明细,
        "参数": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "地市名，例如 南京、苏州、无锡"},
            },
            "required": ["city"],
        },
        "说明": "获取单个地市的完整明细：各专业的退服数与告警数、该市退服合计与告警合计",
    },
}


def 工具清单():
    """把工具表转成 OpenAI tools 格式——LLM 只凭 name/description/参数说明决定怎么调"""
    return [
        {
            "type": "function",
            "function": {
                "name": 名,
                "description": 信息["说明"],
                "parameters": 信息["参数"],
            },
        }
        for 名, 信息 in 工具表.items()
    ]


def 执行工具(调用):
    """执行一次模型要求的工具调用。任何失败都不抛异常，
    而是把错误作为结果返回——回填给模型，让它自行纠正。"""
    名 = 调用.function.name
    try:
        参数 = json.loads(调用.function.arguments or "{}")   # 模型给的参数是 JSON 文本
    except json.JSONDecodeError:
        return 名, {}, {"error": "参数不是合法 JSON"}
    if 名 not in 工具表:
        return 名, 参数, {"error": f"未知工具：{名}"}
    try:
        return 名, 参数, 工具表[名]["函数"](**参数)
    except TypeError as 错:
        return 名, 参数, {"error": f"参数不匹配：{错}"}
    except requests.RequestException as 错:
        return 名, 参数, {"error": f"工具执行失败：{错}"}


# ---------- 循环层 ----------

系统提示 = (项目目录 / "prompts" / "agent.txt").read_text(encoding="utf-8")


def 运行Agent(任务, 最大轮数=8, 打印=False):
    """Agent 的全部状态就是这份 messages 列表——每轮都完整重发。

    返回 {"answer": 最终答案, "trace": 工具调用轨迹, "rounds": 轮数}，
    轨迹供前端展示"Agent 都做了什么"。
    """
    messages = [
        {"role": "system", "content": 系统提示},
        {"role": "user", "content": 任务},
    ]
    轨迹 = []

    for 轮 in range(1, 最大轮数 + 1):
        应答 = 客户端.chat.completions.create(
            model=模型名,
            messages=messages,
            tools=工具清单(),
            temperature=0.2,
        )
        if not 应答.choices:
            # 个别服务在拒绝请求时返回 200 但 choices 为空，把原始应答暴露出来
            raise RuntimeError(f"LLM 应答异常，无 choices：{应答.model_dump_json()[:500]}")
        消息 = 应答.choices[0].message

        # 终止条件①：模型不再要求调工具——它给出的就是最终答案
        if not 消息.tool_calls:
            if 打印:
                print(f"\n=== 最终答案（第 {轮} 轮）===\n{消息.content}")
            return {"answer": 消息.content, "trace": 轨迹, "rounds": 轮}

        # 模型要求调工具：这条要求必须原样计入历史（含 tool_call_id）
        messages.append({
            "role": "assistant",
            "content": 消息.content,
            "tool_calls": [调用.model_dump() for 调用 in 消息.tool_calls],
        })

        for 调用 in 消息.tool_calls:
            名, 参数, 结果 = 执行工具(调用)
            结果文本 = json.dumps(结果, ensure_ascii=False)
            轨迹.append({
                "工具": 名,
                "参数": json.dumps(参数, ensure_ascii=False),
                "摘要": 结果文本[:100],
            })
            if 打印:
                print(f"[第 {轮} 轮] 调用 {名} 参数 {参数} → {结果文本[:100]}")
            messages.append({
                "role": "tool",
                "tool_call_id": 调用.id,
                "content": 结果文本,
            })

    # 终止条件②：轮数保护，防止模型陷入无限调用
    if 打印:
        print(f"达到最大轮数 {最大轮数}，终止。")
    return {"answer": None, "error": f"达到最大轮数 {最大轮数}", "trace": 轨迹, "rounds": 最大轮数}


if __name__ == "__main__":
    任务 = sys.argv[1] if len(sys.argv) > 1 else "现在全网状况如何？哪个地市最需要关注？给出诊断结论。"
    print(f"任务：{任务}\n")
    运行Agent(任务, 打印=True)
