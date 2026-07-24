"""手写最小 MCP Server。

MCP（Model Context Protocol）把「工具的说明书 + 调用方式」标准化：
任何实现协议的客户端都能发现并调用本服务的 NOC 工具。

协议本体 = JSON-RPC 2.0，stdio 传输（每行一个消息），三个核心方法：
  initialize / tools/list / tools/call

启动（通常由 MCP 客户端作为子进程拉起）：python3 -m noc_agent.mcp.server
"""
import json
import sys

from ..agent.tools import TOOL_REGISTRY, execute_tool

PROTOCOL_VERSION = "2025-06-18"


def send(payload):
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def respond(msg_id, result):
    send({"jsonrpc": "2.0", "id": msg_id, "result": result})


def respond_error(msg_id, code, message):
    send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def handle(message):
    method, msg_id = message.get("method"), message.get("id")

    if method == "initialize":
        respond(msg_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "telecom-noc-tools", "version": "1.4.0"},
        })

    elif method == "notifications/initialized":
        pass                                  # 通知类消息无 id，不需要应答

    elif method == "tools/list":
        respond(msg_id, {"tools": [
            {"name": name, "description": info["description"], "inputSchema": info["params"]}
            for name, info in TOOL_REGISTRY.items()
        ]})

    elif method == "tools/call":
        name = message["params"]["name"]
        arguments = message["params"].get("arguments", {})
        _, result = execute_tool(name, json.dumps(arguments, ensure_ascii=False))
        respond(msg_id, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": isinstance(result, dict) and "error" in result,
        })

    elif msg_id is not None:
        respond_error(msg_id, -32601, f"未实现的方法：{method}")


if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except Exception as exc:              # 协议服务不能因单条消息崩溃
            respond_error(None, -32603, f"内部错误:{exc}")
