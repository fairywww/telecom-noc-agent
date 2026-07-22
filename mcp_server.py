"""
文件7：手写最小 MCP Server
============================================================
MCP（Model Context Protocol）把「工具的说明书 + 调用方式」标准化：
任何实现了协议的客户端（Claude、Cursor、自研 Agent……）都能发现并
调用本服务暴露的 NOC 工具，无需为每个客户端单写一份接入代码。

协议本体 = JSON-RPC 2.0；本实现用 stdio 传输（每行一个消息），
支持三个核心方法：
  initialize  —— 握手：交换协议版本与能力
  tools/list  —— 工具发现：返回 name/description/inputSchema
  tools/call  —— 工具调用：执行并返回内容

启动（通常由 MCP 客户端作为子进程拉起，不需要手动运行）：
  python3 mcp_server.py
"""
import json
import sys

from tools import 工具表, 执行工具

协议版本 = "2025-06-18"


def 发送(消息体):
    print(json.dumps(消息体, ensure_ascii=False), flush=True)


def 应答(编号, 结果):
    发送({"jsonrpc": "2.0", "id": 编号, "result": 结果})


def 报错(编号, 码, 信息):
    发送({"jsonrpc": "2.0", "id": 编号, "error": {"code": 码, "message": 信息}})


def 处理(消息):
    方法, 编号 = 消息.get("method"), 消息.get("id")

    if 方法 == "initialize":
        应答(编号, {
            "protocolVersion": 协议版本,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "telecom-noc-tools", "version": "0.9.0"},
        })

    elif 方法 == "notifications/initialized":
        pass                                  # 通知类消息无 id，不需要应答

    elif 方法 == "tools/list":
        应答(编号, {"tools": [
            {"name": 名, "description": 信息["说明"], "inputSchema": 信息["参数"]}
            for 名, 信息 in 工具表.items()
        ]})

    elif 方法 == "tools/call":
        名 = 消息["params"]["name"]
        入参 = 消息["params"].get("arguments", {})
        _, 结果 = 执行工具(名, json.dumps(入参, ensure_ascii=False))
        应答(编号, {
            "content": [{"type": "text", "text": json.dumps(结果, ensure_ascii=False)}],
            "isError": isinstance(结果, dict) and "error" in 结果,
        })

    elif 编号 is not None:
        报错(编号, -32601, f"未实现的方法：{方法}")


if __name__ == "__main__":
    for 行 in sys.stdin:
        行 = 行.strip()
        if not 行:
            continue
        try:
            处理(json.loads(行))
        except Exception as 错:                # 协议服务不能因单条消息崩溃
            报错(None, -32603, f"内部错误:{错}")
