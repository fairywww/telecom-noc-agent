"""MCP 协议测试：握手与工具发现（不执行工具，零网络依赖）"""
import json
import subprocess
import sys
from pathlib import Path

仓库根 = Path(__file__).parent.parent


def _往返(进程, 消息):
    进程.stdin.write(json.dumps(消息, ensure_ascii=False) + "\n")
    进程.stdin.flush()
    return json.loads(进程.stdout.readline())


def test_mcp_握手与工具发现():
    进程 = subprocess.Popen(
        [sys.executable, str(仓库根 / "mcp_server.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=仓库根,
    )
    try:
        握手 = _往返(进程, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-06-18",
                                     "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}})
        assert 握手["result"]["serverInfo"]["name"] == "telecom-noc-tools"

        清单 = _往返(进程, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        名字们 = {工具["name"] for 工具 in 清单["result"]["tools"]}
        assert {"查全网概览", "查运维知识"} <= 名字们
        assert all("inputSchema" in 工具 for 工具 in 清单["result"]["tools"])

        未知 = _往返(进程, {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}})
        assert 未知["error"]["code"] == -32601
    finally:
        进程.terminate()
