"""
最小 MCP 客户端演示：与 mcp_server.py 走完整协议流程
============================================================
把 server 作为子进程拉起（MCP stdio 模式的标准做法），依次演示：
  ① initialize 握手 → ② tools/list 发现工具 → ③④ tools/call 调用

运行：python3 mcp_client_demo.py   （工具真实执行需要 8001/8002 在运行）
"""
import json
import subprocess
import sys
from pathlib import Path

服务进程 = subprocess.Popen(
    [sys.executable, str(Path(__file__).parent / "mcp_server.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
)
编号 = 0


def 请求(方法, 参数=None):
    global 编号
    编号 += 1
    服务进程.stdin.write(json.dumps(
        {"jsonrpc": "2.0", "id": 编号, "method": 方法, "params": 参数 or {}},
        ensure_ascii=False) + "\n")
    服务进程.stdin.flush()
    return json.loads(服务进程.stdout.readline())["result"]


def 通知(方法):
    服务进程.stdin.write(json.dumps({"jsonrpc": "2.0", "method": 方法}) + "\n")
    服务进程.stdin.flush()


if __name__ == "__main__":
    握手 = 请求("initialize", {"protocolVersion": "2025-06-18",
                              "capabilities": {}, "clientInfo": {"name": "demo", "version": "0"}})
    print("① 握手成功：", 握手["serverInfo"])
    通知("notifications/initialized")

    工具们 = 请求("tools/list")["tools"]
    print("② 发现工具：", [工具["name"] for 工具 in 工具们])

    应答 = 请求("tools/call", {"name": "查全网概览", "arguments": {}})
    print("③ 调用 查全网概览 →", 应答["content"][0]["text"])

    应答 = 请求("tools/call", {"name": "查指定地市明细", "arguments": {"city": "苏州"}})
    print("④ 调用 查指定地市明细(苏州) →", 应答["content"][0]["text"][:90], "…")

    服务进程.terminate()
