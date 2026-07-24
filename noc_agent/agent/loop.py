"""手写 Agent 循环——本项目的核心。

不依赖任何 Agent 框架。循环只有一条规则：

    LLM 推理 → 要求调工具? → 执行工具、结果回填对话历史 → 再推理
                └─ 不要求 → 它给出的就是最终答案，结束

核心实现是生成器 run_agent_stream()：边执行边产出事件。
命令行、评测、SSE 接口消费同一个生成器——一份循环逻辑，三种用途。

用法：python3 -m noc_agent.agent.loop "苏州的情况怎么样？"
（需要 8001/8002 两个服务在运行）
"""
import json
import sys

from ..config import prompt
from ..llm import MODEL, client
from .tools import TOOL_REGISTRY, execute_tool, tool_specs

DEFAULT_SYSTEM_PROMPT = prompt("agent.txt")


def run_agent_stream(task, max_rounds=8, toolset=None, system_prompt=None, history=None):
    """核心生成器：执行 Agent 循环，边执行边产出事件字典。

    toolset / system_prompt 可定制——同一个循环既能当默认诊断 Agent，
    也能装上不同的"人设 + 工具箱"充当专家子 Agent（见 orchestrator.py）。

    事件类型：
      {"event":"text",  "text": 增量}                       —— 答案逐字产出
      {"event":"tool",  "tool":名, "args":…, "summary":…}   —— 一次工具调用完成
      {"event":"info",  "text": …}                          —— 重试等过程信息
      {"event":"done",  "rounds":n, "tokens":m}             —— 正常结束
      {"event":"error", "message": …}                       —— 异常结束
    """
    toolset = toolset or TOOL_REGISTRY
    messages = (
        [{"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT}]
        + list(history or [])                    # 多轮对话：历史由调用方维护（见 memory.py）
        + [{"role": "user", "content": task}]
    )
    total_tokens = 0

    for round_no in range(1, max_rounds + 1):
        # ---- 发起流式请求（空应答自动重试：评测中复现过该服务端抖动）----
        for attempt in range(3):
            stream = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tool_specs(toolset),
                temperature=0.2,
                stream=True,
                stream_options={"include_usage": True},
            )
            content_parts = []
            pending_calls = {}     # tool_calls 以碎片流式到达：按 index 逐段拼接
            got_data = False
            for chunk in stream:
                if chunk.usage:
                    total_tokens += chunk.usage.total_tokens
                if not chunk.choices:
                    continue
                got_data = True
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                    yield {"event": "text", "text": delta.content}
                for fragment in (delta.tool_calls or []):
                    entry = pending_calls.setdefault(
                        fragment.index, {"id": "", "name": "", "arguments": ""})
                    if fragment.id:
                        entry["id"] = fragment.id
                    if fragment.function and fragment.function.name:
                        entry["name"] = fragment.function.name
                    if fragment.function and fragment.function.arguments:
                        entry["arguments"] += fragment.function.arguments
            if got_data:
                break
            yield {"event": "info", "text": f"服务端返回空应答，重试 {attempt + 1}/3"}
        else:
            yield {"event": "error", "message": "LLM 连续 3 次返回空应答"}
            return

        # ---- 终止条件①：没有工具调用，本轮内容就是最终答案 ----
        if not pending_calls:
            yield {"event": "done", "rounds": round_no, "tokens": total_tokens}
            return

        # ---- 有工具调用：原样入史，逐个执行并回填 ----
        tool_calls = [
            {"id": entry["id"], "type": "function",
             "function": {"name": entry["name"], "arguments": entry["arguments"]}}
            for _, entry in sorted(pending_calls.items())
        ]
        messages.append({"role": "assistant", "content": "".join(content_parts),
                         "tool_calls": tool_calls})
        for call in tool_calls:
            args, result = execute_tool(call["function"]["name"],
                                        call["function"]["arguments"], toolset)
            result_text = json.dumps(result, ensure_ascii=False)
            yield {"event": "tool", "tool": call["function"]["name"],
                   "args": json.dumps(args, ensure_ascii=False),
                   "summary": result_text[:100]}
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": result_text})

    # ---- 终止条件②：轮数保护，防止无限调用 ----
    yield {"event": "error", "message": f"达到最大轮数 {max_rounds}"}


def run_agent(task, max_rounds=8, verbose=False, toolset=None, system_prompt=None, history=None):
    """非流式封装：消费生成器，攒出完整结果。命令行与评测用它。"""
    answer_parts, trace = [], []
    rounds = tokens = 0
    error = None
    for event in run_agent_stream(task, max_rounds, toolset, system_prompt, history):
        if event["event"] == "text":
            answer_parts.append(event["text"])
            if verbose:
                print(event["text"], end="", flush=True)
        elif event["event"] == "tool":
            trace.append({"tool": event["tool"], "args": event["args"],
                          "summary": event["summary"]})
            if verbose:
                print(f"[工具] {event['tool']} {event['args']} → {event['summary']}")
        elif event["event"] == "done":
            rounds, tokens = event["rounds"], event["tokens"]
        elif event["event"] in ("info", "error"):
            error = event.get("message")
            if verbose:
                print(f"[{event['event']}] {event.get('text') or event.get('message')}")
    if verbose:
        print()
    result = {"answer": "".join(answer_parts) or None, "trace": trace,
              "rounds": rounds, "tokens": tokens}
    if error and not result["answer"]:
        result["error"] = error
    return result


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "现在全网状况如何？哪个地市最需要关注？给出诊断结论。"
    print(f"任务：{task}\n")
    run_agent(task, verbose=True)
