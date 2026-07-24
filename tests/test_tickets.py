"""工单存储测试：创建、幂等保护、列表、API 契约（临时库文件，零网络依赖）"""
from fastapi.testclient import TestClient

from noc_agent.storage import tickets


def _use_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(tickets, "DB_PATH", tmp_path / "tickets.db")


def test_create_ticket(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    result = tickets.create_ticket("南京", "退服64站，占全网41.8%", "启动应急预案", 4)
    assert result["created"] and result["ticket_id"] == 1
    assert result["status"] == "待处理"


def test_idempotency_same_city_open_ticket(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    tickets.create_ticket("南京", "第一单", "处置", 4)
    duplicate = tickets.create_ticket("南京", "第二单", "处置", 4)
    assert "error" in duplicate and duplicate["existing_ticket_id"] == 1
    assert len(tickets.list_tickets()) == 1          # 确实没建第二张


def test_different_cities_independent(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    tickets.create_ticket("南京", "a", "b", 4)
    result = tickets.create_ticket("苏州", "c", "d", 8)
    assert result["created"] and result["ticket_id"] == 2


def test_api_contract(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    from noc_agent.server import adapter
    client = TestClient(adapter.app)
    response = client.post("/api/tickets", json={
        "city": "无锡", "summary": "退服31站", "action": "按五步处置法处理"})
    assert response.json()["created"]
    listed = client.get("/api/tickets").json()["tickets"]
    assert listed[0]["city"] == "无锡" and listed[0]["deadline_hours"] == 8   # 默认时限
