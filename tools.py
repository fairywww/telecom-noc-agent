"""
文件6：工具层 —— 与 Agent 循环解耦的工具定义
============================================================
每个工具 = 一段说明 + 一份参数 schema + 一个普通函数。
两个消费方：
  - agent.py 的循环（经 OpenAI tools 格式交给 LLM）
  - mcp_server.py（经 MCP 协议暴露给任何 MCP 客户端）
工具与消费方分离，正是 MCP 想标准化的那条边界。
"""
import json

import requests

大屏后端 = "http://localhost:8002"


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
    """执行一次工具调用。任何失败都不抛异常，
    而是把错误作为结果返回——回填给调用方，让其自行纠正。"""
    try:
        参数 = json.loads(参数文本 or "{}")
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
