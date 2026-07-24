"""
文件10：LangGraph 版诊断 Agent —— 与手写循环（agent.py）逐概念对照
============================================================
同一个 Agent，第二种写法。目的不是替换手写版，而是看清框架
封装了什么：

    手写版（agent.py）              LangGraph 版（本文件）
    messages 列表                → State（MessagesState）
    while 循环 + if tool_calls   → 图：节点 + 条件边
    工具表 + 执行工具()           → ToolNode（自动执行并回填）
    自己拼 assistant/tool 消息    → 框架代管消息格式

依赖（不在核心 requirements 内）：pip install langgraph langchain-openai
用法：python3 langgraph_agent.py "哪个地市最需要关注？"
"""
import os
import sys

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

from llm import 项目目录, 模型名
import tools as 工具模块

# ---- ① 模型：同一个 OpenAI 兼容端点，换个客户端封装 ----
模型 = ChatOpenAI(
    model=模型名,
    base_url=os.environ.get("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.environ["LLM_API_KEY"],
    temperature=0.2,
)


# ---- ② 工具：@tool 装饰器从函数签名和 docstring 生成 schema ----
#（手写版里我们自己写 JSON Schema；框架从代码里"读"出来）

@tool
def 查全网概览() -> dict:
    """获取全网汇总指标：退服总数 outage_total、告警总数 alarm_total、覆盖地市数 city_count"""
    return 工具模块.查全网概览()


@tool
def 查地市退服明细() -> dict:
    """获取逐地市退服明细：各地市分专业(4G/5G)退服数与合计，已按严重程度降序排列"""
    return 工具模块.查地市退服明细()


@tool
def 查指定地市明细(city: str) -> dict:
    """获取单个地市的完整明细：各专业的退服数与告警数、该市退服合计与告警合计。city 为地市名，例如 南京、苏州、无锡"""
    return 工具模块.查指定地市明细(city)


@tool
def 查运维知识(query: str) -> dict:
    """检索运维知识库（处置流程、告警等级、退服常见原因、指标口径等规范资料）。回答制度、流程、定义类问题时使用"""
    return 工具模块.查运维知识(query)


工具们 = [查全网概览, 查地市退服明细, 查指定地市明细, 查运维知识]
带工具的模型 = 模型.bind_tools(工具们)

系统提示 = (项目目录 / "prompts" / "agent.txt").read_text(encoding="utf-8")


# ---- ③ 图：两个节点 + 一条条件边，等价于手写版的 while 循环 ----

def 推理节点(state: MessagesState):
    """对应手写版的「调一次 LLM」：输入全部历史，输出一条新消息"""
    应答 = 带工具的模型.invoke(state["messages"])
    return {"messages": [应答]}


def 是否继续(state: MessagesState):
    """对应手写版的「if not tool_calls: 结束」这一行"""
    最后一条 = state["messages"][-1]
    return "工具节点" if getattr(最后一条, "tool_calls", None) else END


图 = StateGraph(MessagesState)
图.add_node("推理节点", 推理节点)
图.add_node("工具节点", ToolNode(工具们))     # 对应手写版的 执行工具 + 回填
图.add_edge(START, "推理节点")
图.add_conditional_edges("推理节点", 是否继续, {"工具节点": "工具节点", END: END})
图.add_edge("工具节点", "推理节点")            # 工具执行完回到推理——循环闭合
应用 = 图.compile()


def 运行(任务, 打印=True):
    状态 = 应用.invoke(
        {"messages": [("system", 系统提示), ("user", 任务)]},
        config={"recursion_limit": 16},        # 对应手写版的最大轮数保护
    )
    if 打印:
        for 消息 in 状态["messages"]:
            类型 = 消息.__class__.__name__
            if 类型 == "AIMessage" and getattr(消息, "tool_calls", None):
                for 调用 in 消息.tool_calls:
                    print(f"[工具] {调用['name']} {调用['args']}")
            elif 类型 == "AIMessage" and 消息.content:
                print(f"\n=== 最终答案 ===\n{消息.content}")
    return 状态["messages"][-1].content


if __name__ == "__main__":
    任务 = sys.argv[1] if len(sys.argv) > 1 else "现在全网状况如何？哪个地市最需要关注？"
    print(f"任务：{任务}\n")
    运行(任务)
