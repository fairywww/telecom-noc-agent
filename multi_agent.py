"""
文件8：多 Agent 协作 —— 总控 + 专家子 Agent
============================================================
架构（Agent as Tool 模式）：

            总控 Agent（编排，不直接查数据）
             |                     |
      咨询数据分析专家        咨询知识规范专家     ← 对总控而言只是两个"工具"
             |                     |
      数据分析子 Agent        知识规范子 Agent    ← 各自是完整的 Agent 循环
      （三个指标工具）         （查运维知识）

没有新机制：子 Agent 就是"装了不同人设与工具箱的 运行Agent()"，
再包成一个函数注册进总控的工具表。循环还是那一个循环。

用法：python3 multi_agent.py "南京情况多严重？按规范怎么处置？"
"""
import sys

from agent import 运行Agent
from llm import 项目目录
from tools import 工具表


def 加载提示(文件名):
    return (项目目录 / "prompts" / 文件名).read_text(encoding="utf-8")


专家消耗记录 = []    # 每次专家咨询的开销，供成本对比与评测使用


def 建专家(名字, 提示文件, 工具名单, 说明):
    """把一个子 Agent 包装成总控可用的工具：
    子 Agent 只拿到自己职责内的工具子集与专属人设。"""
    提示 = 加载提示(提示文件)
    子工具集 = {名: 工具表[名] for 名 in 工具名单}

    def 咨询(task):
        结果 = 运行Agent(task, 工具集=子工具集, 系统提示文本=提示)
        专家消耗记录.append({"专家": 名字, "词元": 结果["tokens"], "轮数": 结果["rounds"]})
        return {
            "专家": 名字,
            "结论": 结果["answer"] or 结果.get("error", "（无结论）"),
            "调用工具次数": len(结果["trace"]),
            "词元": 结果["tokens"],
        }

    return {
        "函数": 咨询,
        "参数": {
            "type": "object",
            "properties": {"task": {"type": "string", "description": "交给该专家的具体子任务，须自包含、无歧义"}},
            "required": ["task"],
        },
        "说明": 说明,
    }


总控工具集 = {
    "咨询数据分析专家": 建专家(
        "数据分析专家", "data_analyst.txt",
        ["查全网概览", "查地市退服明细", "查指定地市明细"],
        "将需要实时网络指标的任务（退服/告警数字、地市排名、量化对比）交给数据分析专家",
    ),
    "咨询知识规范专家": 建专家(
        "知识规范专家", "knowledge_expert.txt",
        ["查运维知识"],
        "将制度、流程、定义类问题（处置流程、告警等级、指标口径）交给知识规范专家",
    ),
}


def 运行总控(任务, 打印=False):
    return 运行Agent(任务, 最大轮数=6, 打印=打印,
                     工具集=总控工具集, 系统提示文本=加载提示("orchestrator.txt"))


if __name__ == "__main__":
    任务 = sys.argv[1] if len(sys.argv) > 1 else "南京退服全网最多，情况有多严重？按规范接下来该怎么处置？"
    print(f"任务：{任务}\n")
    运行总控(任务, 打印=True)
