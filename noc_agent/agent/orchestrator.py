"""多 Agent 协作：总控 + 专家子 Agent（Agent as Tool 模式）。

            总控 Agent（编排，不直接查数据）
             |                     |
     consult_data_analyst   consult_knowledge_expert   ← 对总控只是两个工具
             |                     |
      数据分析子 Agent        知识规范子 Agent           ← 各自是完整的 Agent 循环

没有新机制：子 Agent = 装上专属人设与受限工具箱的同一个循环，
再包成一个函数注册进总控的工具表。

用法：python3 -m noc_agent.agent.orchestrator "南京情况多严重？按规范怎么处置？"
"""
import sys

from ..config import prompt
from .loop import run_agent
from .tools import TOOL_REGISTRY

EXPERT_USAGE = []    # 每次专家咨询的开销，供成本对比与评测使用


def build_expert(name, prompt_file, tool_names, description):
    """把一个子 Agent 包装成总控可用的工具：
    子 Agent 只拿到自己职责内的工具子集与专属人设。"""
    persona = prompt(prompt_file)
    sub_toolset = {tool: TOOL_REGISTRY[tool] for tool in tool_names}

    def consult(task):
        result = run_agent(task, toolset=sub_toolset, system_prompt=persona)
        EXPERT_USAGE.append({"expert": name, "tokens": result["tokens"],
                             "rounds": result["rounds"]})
        return {
            "expert": name,
            "conclusion": result["answer"] or result.get("error", "（无结论）"),
            "tool_calls": len(result["trace"]),
            "tokens": result["tokens"],
        }

    return {
        "func": consult,
        "params": {
            "type": "object",
            "properties": {"task": {"type": "string",
                                    "description": "交给该专家的具体子任务，须自包含、无歧义"}},
            "required": ["task"],
        },
        "description": description,
    }


ORCHESTRATOR_TOOLS = {
    "consult_data_analyst": build_expert(
        "数据分析专家", "data_analyst.txt",
        ["get_network_overview", "get_city_outages", "get_city_detail"],
        "将需要实时网络指标的任务（退服/告警数字、地市排名、量化对比）交给数据分析专家",
    ),
    "consult_knowledge_expert": build_expert(
        "知识规范专家", "knowledge_expert.txt",
        ["search_ops_knowledge"],
        "将制度、流程、定义类问题（处置流程、告警等级、指标口径）交给知识规范专家",
    ),
}


def run_orchestrator(task, verbose=False):
    return run_agent(task, max_rounds=6, verbose=verbose,
                     toolset=ORCHESTRATOR_TOOLS, system_prompt=prompt("orchestrator.txt"))


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "南京退服全网最多，情况有多严重？按规范接下来该怎么处置？"
    print(f"任务：{task}\n")
    run_orchestrator(task, verbose=True)
