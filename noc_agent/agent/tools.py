"""工具层：与 Agent 循环解耦的工具定义。

每个工具 = 一段说明 + 一份参数 schema + 一个普通函数。
两个消费方：Agent 循环（OpenAI tools 格式）与 MCP Server（MCP 协议）。
工具与消费方之间的边界，正是 MCP 标准化的对象。
"""
import json
import os

import requests

DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8002")


def get_network_overview():
    return requests.get(f"{DASHBOARD_URL}/api/kpi", timeout=5).json()


def get_city_outages():
    return requests.get(f"{DASHBOARD_URL}/api/city-outage", timeout=5).json()


def get_city_detail(city):
    return requests.get(f"{DASHBOARD_URL}/api/city-detail", params={"city": city}, timeout=5).json()


def search_ops_knowledge(query):
    from ..rag.retrieval import search   # 延迟导入：首次调用时才构建向量索引
    return {"hits": search(query, top_k=3)}


def create_ticket(city, summary, action, deadline_hours=8):
    response = requests.post(f"{DASHBOARD_URL}/api/tickets", timeout=5, json={
        "city": city, "summary": summary, "action": action, "deadline_hours": deadline_hours,
    })
    return response.json()


NO_PARAMS = {"type": "object", "properties": {}, "required": []}

TOOL_REGISTRY = {
    "get_network_overview": {
        "func": get_network_overview,
        "params": NO_PARAMS,
        "description": "获取全网汇总指标：退服总数 outage_total、告警总数 alarm_total、覆盖地市数 city_count",
    },
    "get_city_outages": {
        "func": get_city_outages,
        "params": NO_PARAMS,
        "description": "获取逐地市退服明细：各地市分专业(4G/5G)退服数与合计，已按严重程度降序排列",
    },
    "get_city_detail": {
        "func": get_city_detail,
        "params": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "地市名，例如 南京、苏州、无锡"},
            },
            "required": ["city"],
        },
        "description": "获取单个地市的完整明细：各专业的退服数与告警数、该市退服合计与告警合计",
    },
    "search_ops_knowledge": {
        "func": search_ops_knowledge,
        "params": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "要查询的知识主题，例如：退服处置流程、告警等级定义、退服常见原因"},
            },
            "required": ["query"],
        },
        "description": "检索运维知识库（处置流程、告警等级、退服常见原因、指标口径等规范资料）。"
                       "回答制度、流程、定义类问题时使用；实时数字指标请用其他工具。",
    },
    "create_ticket": {
        "func": create_ticket,
        "params": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "故障所属地市，例如 南京"},
                "summary": {"type": "string", "description": "故障摘要：现象与关键数字，一两句话"},
                "action": {"type": "string", "description": "处置建议：依据规范给出的具体动作"},
                "deadline_hours": {"type": "integer", "description": "处置时限（小时），依据规范的响应时限要求，默认 8"},
            },
            "required": ["city", "summary", "action"],
        },
        "description": "创建故障处置工单（写操作，会真实生成一张工单）。"
                       "仅在用户明确要求建单/派单时调用；同一地市已有待处理工单时系统会拒绝重复创建。",
    },
}


def tool_specs(toolset=None):
    """转成 OpenAI tools 格式——LLM 只凭 name/description/参数说明决定怎么调"""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": info["description"],
                "parameters": info["params"],
            },
        }
        for name, info in (toolset or TOOL_REGISTRY).items()
    ]


def execute_tool(name, args_text, toolset=None):
    """执行一次工具调用。任何失败都不抛异常，而是把错误作为结果
    返回——回填给模型，让它自行纠正（错误是数据，不是事故）。"""
    toolset = toolset or TOOL_REGISTRY
    try:
        args = json.loads(args_text or "{}")
    except json.JSONDecodeError:
        return {}, {"error": "参数不是合法 JSON"}
    if name not in toolset:
        return args, {"error": f"未知工具：{name}"}
    try:
        return args, toolset[name]["func"](**args)
    except TypeError as exc:
        return args, {"error": f"参数不匹配：{exc}"}
    except requests.RequestException as exc:
        return args, {"error": f"工具执行失败：{exc}"}
