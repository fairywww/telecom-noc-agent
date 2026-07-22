"""
文件4：手写 Agent 循环 —— 本仓库的核心
============================================================
不用任何 Agent 框架。循环只有一条规则：

    LLM 推理 → 要求调工具? → 执行工具、结果回填对话历史 → 再推理
                └─ 不要求 → 它给出的就是最终答案，结束

核心实现是一个**生成器** 运行Agent流()：边执行边产出事件
（文字增量 / 工具调用 / 完成 / 错误）。命令行、评测、SSE 接口
消费的是同一个生成器——一份循环逻辑，三种用途。

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


def 查运维知识(query):
    from rag import 检索          # 延迟导入：首次调用时才构建向量索引
    return {"命中": 检索(query, top_k=3)}


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
    "查运维知识": {
        "函数": 查运维知识,
        "参数": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "要查询的知识主题，例如：退服处置流程、告警等级定义、退服常见原因"},
            },
            "required": ["query"],
        },
        "说明": "检索运维知识库（处置流程、告警等级、退服常见原因、指标口径等规范资料）。"
               "回答制度、流程、定义类问题时使用；实时数字指标请用其他工具。",
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


def 执行工具(名, 参数文本):
    """执行一次模型要求的工具调用。任何失败都不抛异常，
    而是把错误作为结果返回——回填给模型，让它自行纠正。"""
    try:
        参数 = json.loads(参数文本 or "{}")   # 模型给的参数是 JSON 文本
    except json.JSONDecodeError:
        return {}, {"error": "参数不是合法 JSON"}
    if 名 not in 工具表:
        return 参数, {"error": f"未知工具：{名}"}
    try:
        return 参数, 工具表[名]["函数"](**参数)
    except TypeError as 错:
        return 参数, {"error": f"参数不匹配：{错}"}
    except requests.RequestException as 错:
        return 参数, {"error": f"工具执行失败：{错}"}


# ---------- 循环层 ----------

系统提示 = (项目目录 / "prompts" / "agent.txt").read_text(encoding="utf-8")


def 运行Agent流(任务, 最大轮数=8):
    """核心生成器：执行 Agent 循环，边执行边产出事件字典。

    事件类型：
      {"事件":"文字",  "文本": 增量}                    —— 答案逐字产出
      {"事件":"工具",  "工具":名, "参数":…, "摘要":…}   —— 一次工具调用完成
      {"事件":"提示",  "文本": …}                       —— 重试等过程信息
      {"事件":"完成",  "轮数":n, "词元":m}              —— 正常结束
      {"事件":"错误",  "信息": …}                       —— 异常结束
    """
    messages = [
        {"role": "system", "content": 系统提示},
        {"role": "user", "content": 任务},
    ]
    总词元 = 0

    for 轮 in range(1, 最大轮数 + 1):
        # ---- 发起流式请求（空应答自动重试，评测中曾复现该服务端抖动）----
        for 重试 in range(3):
            应答流 = 客户端.chat.completions.create(
                model=模型名,
                messages=messages,
                tools=工具清单(),
                temperature=0.2,
                stream=True,
                stream_options={"include_usage": True},
            )
            内容段 = []
            组装中 = {}      # tool_calls 以碎片流式到达：按 index 逐段拼接
            有数据 = False
            for 块 in 应答流:
                if 块.usage:
                    总词元 += 块.usage.total_tokens
                if not 块.choices:
                    continue
                有数据 = True
                增量 = 块.choices[0].delta
                if 增量.content:
                    内容段.append(增量.content)
                    yield {"事件": "文字", "文本": 增量.content}
                for 碎片 in (增量.tool_calls or []):
                    条 = 组装中.setdefault(碎片.index, {"id": "", "name": "", "arguments": ""})
                    if 碎片.id:
                        条["id"] = 碎片.id
                    if 碎片.function and 碎片.function.name:
                        条["name"] = 碎片.function.name
                    if 碎片.function and 碎片.function.arguments:
                        条["arguments"] += 碎片.function.arguments
            if 有数据:
                break
            yield {"事件": "提示", "文本": f"服务端返回空应答，重试 {重试 + 1}/3"}
        else:
            yield {"事件": "错误", "信息": "LLM 连续 3 次返回空应答"}
            return

        # ---- 终止条件①：没有工具调用，本轮内容就是最终答案 ----
        if not 组装中:
            yield {"事件": "完成", "轮数": 轮, "词元": 总词元}
            return

        # ---- 有工具调用：原样入史，逐个执行并回填 ----
        工具调用列表 = [
            {"id": 条["id"], "type": "function",
             "function": {"name": 条["name"], "arguments": 条["arguments"]}}
            for _, 条 in sorted(组装中.items())
        ]
        messages.append({"role": "assistant", "content": "".join(内容段),
                         "tool_calls": 工具调用列表})
        for 调用 in 工具调用列表:
            参数, 结果 = 执行工具(调用["function"]["name"], 调用["function"]["arguments"])
            结果文本 = json.dumps(结果, ensure_ascii=False)
            yield {"事件": "工具", "工具": 调用["function"]["name"],
                   "参数": json.dumps(参数, ensure_ascii=False), "摘要": 结果文本[:100]}
            messages.append({"role": "tool", "tool_call_id": 调用["id"], "content": 结果文本})

    # ---- 终止条件②：轮数保护 ----
    yield {"事件": "错误", "信息": f"达到最大轮数 {最大轮数}"}


def 运行Agent(任务, 最大轮数=8, 打印=False):
    """非流式封装：消费生成器，攒出完整结果。命令行与评测用它。"""
    答案段, 轨迹 = [], []
    轮数 = 词元 = 0
    错误 = None
    for 事 in 运行Agent流(任务, 最大轮数):
        if 事["事件"] == "文字":
            答案段.append(事["文本"])
            if 打印:
                print(事["文本"], end="", flush=True)
        elif 事["事件"] == "工具":
            轨迹.append({"工具": 事["工具"], "参数": 事["参数"], "摘要": 事["摘要"]})
            if 打印:
                print(f"[工具] {事['工具']} {事['参数']} → {事['摘要']}")
        elif 事["事件"] == "完成":
            轮数, 词元 = 事["轮数"], 事["词元"]
        elif 事["事件"] in ("提示", "错误"):
            错误 = 事.get("信息")
            if 打印:
                print(f"[{事['事件']}] {事.get('文本') or 事.get('信息')}")
    if 打印:
        print()
    结果 = {"answer": "".join(答案段) or None, "trace": 轨迹, "rounds": 轮数, "tokens": 词元}
    if 错误 and not 结果["answer"]:
        结果["error"] = 错误
    return 结果


if __name__ == "__main__":
    任务 = sys.argv[1] if len(sys.argv) > 1 else "现在全网状况如何？哪个地市最需要关注？给出诊断结论。"
    print(f"任务：{任务}\n")
    运行Agent(任务, 打印=True)
