"""最小 MCP 客户端演示：与 noc_agent.mcp.server 走完整协议流程。

把 Server 作为子进程拉起（MCP stdio 模式的标准做法），依次演示：
  ① initialize 握手 → ② tools/list 发现工具 → ③④ tools/call 调用

运行（仓库根目录）：python3 examples/mcp_client_demo.py
（工具真实执行需要 8001/8002 两个服务在运行）
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

server = subprocess.Popen(
    [sys.executable, "-m", "noc_agent.mcp.server"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=PROJECT_ROOT,
)
_id = 0


def request(method, params=None):
    global _id
    _id += 1
    server.stdin.write(json.dumps(
        {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}},
        ensure_ascii=False) + "\n")
    server.stdin.flush()
    return json.loads(server.stdout.readline())["result"]


def notify(method):
    server.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
    server.stdin.flush()


if __name__ == "__main__":
    init = request("initialize", {"protocolVersion": "2025-06-18",
                                  "capabilities": {}, "clientInfo": {"name": "demo", "version": "0"}})
    print("① 握手成功：", init["serverInfo"])
    notify("notifications/initialized")

    tools = request("tools/list")["tools"]
    print("② 发现工具：", [tool["name"] for tool in tools])

    result = request("tools/call", {"name": "get_network_overview", "arguments": {}})
    print("③ 调用 get_network_overview →", result["content"][0]["text"])

    result = request("tools/call", {"name": "get_city_detail", "arguments": {"city": "苏州"}})
    print("④ 调用 get_city_detail(苏州) →", result["content"][0]["text"][:90], "…")

    server.terminate()
