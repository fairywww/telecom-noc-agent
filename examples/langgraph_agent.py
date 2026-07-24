"""LangGraph 版诊断 Agent——与手写循环（noc_agent/agent/loop.py）逐概念对照。

    手写版                          LangGraph 版（本文件）
    messages 列表                → State（MessagesState）
    while 循环 + if tool_calls   → 图：节点 + 条件边
    TOOL_REGISTRY + execute_tool → ToolNode（自动执行并回填）
    自己拼 assistant/tool 消息    → 框架代管消息格式

依赖（不在核心 requirements 内）：pip install -r requirements-optional.txt
运行（仓库根目录）：python3 examples/langgraph_agent.py "哪个地市最需要关注？"
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 示例脚本直跑时可导入 noc_agent

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

from noc_agent.agent import tools as noc_tools
from noc_agent.config import prompt
from noc_agent.llm import MODEL

# ---- ① 模型：同一个 OpenAI 兼容端点，换个客户端封装 ----
model = ChatOpenAI(
    model=MODEL,
    base_url=os.environ.get("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.environ["LLM_API_KEY"],
    temperature=0.2,
)


# ---- ② 工具：@tool 装饰器从函数签名和 docstring 生成 schema ----

@tool
def get_network_overview() -> dict:
    """获取全网汇总指标：退服总数 outage_total、告警总数 alarm_total、覆盖地市数 city_count"""
    return noc_tools.get_network_overview()


@tool
def get_city_outages() -> dict:
    """获取逐地市退服明细：各地市分专业(4G/5G)退服数与合计，已按严重程度降序排列"""
    return noc_tools.get_city_outages()


@tool
def get_city_detail(city: str) -> dict:
    """获取单个地市的完整明细：各专业的退服数与告警数。city 为地市名，例如 南京、苏州、无锡"""
    return noc_tools.get_city_detail(city)


@tool
def search_ops_knowledge(query: str) -> dict:
    """检索运维知识库（处置流程、告警等级、退服常见原因、指标口径等规范资料）"""
    return noc_tools.search_ops_knowledge(query)


tools = [get_network_overview, get_city_outages, get_city_detail, search_ops_knowledge]
model_with_tools = model.bind_tools(tools)

SYSTEM_PROMPT = prompt("agent.txt")


# ---- ③ 图：两个节点 + 一条条件边，等价于手写版的 while 循环 ----

def reason(state: MessagesState):
    """对应手写版的「调一次 LLM」：输入全部历史，输出一条新消息"""
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: MessagesState):
    """对应手写版的「if not tool_calls: 结束」这一行"""
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


graph = StateGraph(MessagesState)
graph.add_node("reason", reason)
graph.add_node("tools", ToolNode(tools))       # 对应手写版的 execute_tool + 回填
graph.add_edge(START, "reason")
graph.add_conditional_edges("reason", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "reason")              # 工具执行完回到推理——循环闭合
app = graph.compile()


def run(task, verbose=True):
    state = app.invoke(
        {"messages": [("system", SYSTEM_PROMPT), ("user", task)]},
        config={"recursion_limit": 16},         # 对应手写版的最大轮数保护
    )
    if verbose:
        for message in state["messages"]:
            kind = message.__class__.__name__
            if kind == "AIMessage" and getattr(message, "tool_calls", None):
                for call in message.tool_calls:
                    print(f"[工具] {call['name']} {call['args']}")
            elif kind == "AIMessage" and message.content:
                print(f"\n=== 最终答案 ===\n{message.content}")
    return state["messages"][-1].content


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "现在全网状况如何？哪个地市最需要关注？"
    print(f"任务：{task}\n")
    run(task)
