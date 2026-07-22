"""核心逻辑测试：只测纯函数与接口契约，不碰网络与 LLM。

运行：python3 -m pytest tests/ -v
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient


# ---------- 数据层 ----------

def test_noc后端_信封格式():
    from noc_backend import app
    应答 = TestClient(app).get("/api/statistics/all")
    assert 应答.status_code == 200
    体 = 应答.json()
    assert 体["code"] == 0
    assert "南京" in 体["data"]


# ---------- 适配层 ----------

def test_全网汇总_纯函数():
    from adapter import 全网汇总
    行 = {"甲市": {"4G": {"x": 1}, "5G": {"x": 2}}, "乙市": {"4G": {"x": 3}}}
    assert 全网汇总(行, "x") == 6


def test_kpi契约(monkeypatch):
    """mock 掉对 NOC 的 HTTP 调用，只验证聚合与契约字段"""
    import adapter
    假数据 = {"code": 0, "data": {"南京": {"4G": {"outage_count": 1, "alarm_count": 2}}}}
    monkeypatch.setattr(adapter.requests, "get",
                        lambda *参, **键: SimpleNamespace(json=lambda: 假数据))
    体 = TestClient(adapter.app).get("/api/kpi").json()
    assert 体 == {"outage_total": 1, "alarm_total": 2, "city_count": 1}


def test_未知地市_可自纠错误(monkeypatch):
    import adapter
    假数据 = {"code": 0, "data": {"南京": {}}}
    monkeypatch.setattr(adapter.requests, "get",
                        lambda *参, **键: SimpleNamespace(json=lambda: 假数据))
    体 = TestClient(adapter.app).get("/api/city-detail", params={"city": "常州"}).json()
    assert "error" in 体 and 体["可选地市"] == ["南京"]


# ---------- RAG ----------

def test_知识库切分():
    from rag import 切分知识库
    块列表 = 切分知识库()
    assert len(块列表) >= 8, "四个文档按小节切分后应有足够的块"
    assert all(块["来源"] and 块["小节"] and 块["内容"] for 块 in 块列表)


# ---------- Agent ----------

def test_工具清单_格式():
    from agent import 工具清单, 工具表
    清单 = 工具清单()
    assert {条["function"]["name"] for 条 in 清单} == set(工具表)
    assert all(条["type"] == "function" for 条 in 清单)


def test_执行工具_未知工具不抛异常():
    from agent import 执行工具
    假调用 = SimpleNamespace(id="x", function=SimpleNamespace(name="不存在的工具", arguments="{}"))
    名, 参数, 结果 = 执行工具(假调用)
    assert "error" in 结果


def test_执行工具_非法参数不抛异常():
    from agent import 执行工具
    假调用 = SimpleNamespace(id="x", function=SimpleNamespace(name="查全网概览", arguments="不是JSON"))
    名, 参数, 结果 = 执行工具(假调用)
    assert "error" in 结果
