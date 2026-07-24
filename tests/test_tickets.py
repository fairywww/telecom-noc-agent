"""工单存储测试：创建、幂等保护、列表、API 契约（临时库文件，零网络依赖）"""
from fastapi.testclient import TestClient

import tickets


def _用临时库(monkeypatch, tmp_path):
    monkeypatch.setattr(tickets, "库文件", tmp_path / "tickets.db")


def test_创建工单(monkeypatch, tmp_path):
    _用临时库(monkeypatch, tmp_path)
    结果 = tickets.创建工单("南京", "退服64站，占全网41.8%", "启动应急预案", 4)
    assert 结果["created"] and 结果["工单编号"] == 1
    assert 结果["状态"] == "待处理"


def test_幂等保护_同地市待处理不重复建单(monkeypatch, tmp_path):
    _用临时库(monkeypatch, tmp_path)
    tickets.创建工单("南京", "第一单", "处置", 4)
    重复 = tickets.创建工单("南京", "第二单", "处置", 4)
    assert "error" in 重复 and 重复["已有工单编号"] == 1
    assert len(tickets.工单列表()) == 1          # 确实没建第二张


def test_不同地市互不影响(monkeypatch, tmp_path):
    _用临时库(monkeypatch, tmp_path)
    tickets.创建工单("南京", "a", "b", 4)
    结果 = tickets.创建工单("苏州", "c", "d", 8)
    assert 结果["created"] and 结果["工单编号"] == 2


def test_api契约(monkeypatch, tmp_path):
    _用临时库(monkeypatch, tmp_path)
    import adapter
    客户端 = TestClient(adapter.app)
    应答 = 客户端.post("/api/tickets", json={"city": "无锡", "summary": "退服31站", "action": "按五步处置法处理"})
    assert 应答.json()["created"]
    列表 = 客户端.get("/api/tickets").json()["tickets"]
    assert 列表[0]["地市"] == "无锡" and 列表[0]["时限小时"] == 8   # 默认时限
