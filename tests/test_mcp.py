"""MCP 协议测试：握手与工具发现（不执行工具，零网络依赖）"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _roundtrip(process, message):
    process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())


def test_mcp_handshake_and_tool_discovery():
    process = subprocess.Popen(
        [sys.executable, "-m", "noc_agent.mcp.server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=PROJECT_ROOT,
    )
    try:
        init = _roundtrip(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                    "params": {"protocolVersion": "2025-06-18",
                                               "capabilities": {},
                                               "clientInfo": {"name": "t", "version": "0"}}})
        assert init["result"]["serverInfo"]["name"] == "telecom-noc-tools"

        listed = _roundtrip(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {tool["name"] for tool in listed["result"]["tools"]}
        assert {"get_network_overview", "search_ops_knowledge", "create_ticket"} <= names
        assert all("inputSchema" in tool for tool in listed["result"]["tools"])

        unknown = _roundtrip(process, {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}})
        assert unknown["error"]["code"] == -32601
    finally:
        process.terminate()
