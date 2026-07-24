"""核心逻辑测试：只测纯函数与接口契约，不碰网络与 LLM。

运行：python3 -m pytest tests/ -v
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient


# ---------- 数据层 ----------

def test_noc_mock_envelope():
    from noc_agent.server import noc_mock
    response = TestClient(noc_mock.app).get("/api/statistics/all")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert "南京" in body["data"]


# ---------- 适配层 ----------

def test_aggregate_pure_function():
    from noc_agent.server.adapter import aggregate
    rows = {"甲市": {"4G": {"x": 1}, "5G": {"x": 2}}, "乙市": {"4G": {"x": 3}}}
    assert aggregate(rows, "x") == 6


def test_kpi_contract(monkeypatch):
    """mock 掉对 NOC 的 HTTP 调用，只验证聚合与契约字段"""
    from noc_agent.server import adapter
    fake = {"code": 0, "data": {"南京": {"4G": {"outage_count": 1, "alarm_count": 2}}}}
    monkeypatch.setattr(adapter.requests, "get",
                        lambda *args, **kwargs: SimpleNamespace(json=lambda: fake))
    body = TestClient(adapter.app).get("/api/kpi").json()
    assert body == {"outage_total": 1, "alarm_total": 2, "city_count": 1}


def test_city_detail_unknown_city_self_correctable(monkeypatch):
    from noc_agent.server import adapter
    fake = {"code": 0, "data": {"南京": {}}}
    monkeypatch.setattr(adapter.requests, "get",
                        lambda *args, **kwargs: SimpleNamespace(json=lambda: fake))
    body = TestClient(adapter.app).get("/api/city-detail", params={"city": "常州"}).json()
    assert "error" in body and body["available_cities"] == ["南京"]


# ---------- RAG ----------

def test_knowledge_chunking():
    from noc_agent.rag.retrieval import load_chunks
    chunks = load_chunks()
    assert len(chunks) >= 8, "四个文档按小节切分后应有足够的块"
    assert all(c["source"] and c["section"] and c["content"] for c in chunks)


# ---------- Agent 工具层 ----------

def test_tool_specs_format():
    from noc_agent.agent.tools import TOOL_REGISTRY, tool_specs
    specs = tool_specs()
    assert {item["function"]["name"] for item in specs} == set(TOOL_REGISTRY)
    assert all(item["type"] == "function" for item in specs)


def test_execute_tool_unknown_tool_no_raise():
    from noc_agent.agent.tools import execute_tool
    args, result = execute_tool("no_such_tool", "{}")
    assert "error" in result


def test_execute_tool_bad_json_no_raise():
    from noc_agent.agent.tools import execute_tool
    args, result = execute_tool("get_network_overview", "不是JSON")
    assert "error" in result
