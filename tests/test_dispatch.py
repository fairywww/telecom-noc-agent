"""调度闭环测试：剧本引擎、告警归并、规则预筛、建议单审批门（零网络、零 LLM）"""
from fastapi.testclient import TestClient

from noc_agent import dispatch
from noc_agent.storage import tickets


def _use_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(tickets, "DB_PATH", tmp_path / "t.db")


# ---------- 剧本引擎 ----------

def test_scenario_acts():
    from noc_agent.server import noc_mock
    client = TestClient(noc_mock.app)
    client.post("/api/scenario/reset")

    normal = client.get("/api/alarms").json()
    assert normal["act"]["name"] == "normal"
    assert all(a["type"] != "基站退服" for a in normal["alarms"])

    client.post("/api/scenario/next")                     # 进入风暴幕
    storm = client.get("/api/alarms").json()
    outages = [a for a in storm["alarms"] if a["type"] == "基站退服" and a["status"] == "active"]
    assert len(outages) == 12                             # 超过批量退服阈值

    rows = client.get("/api/statistics/all").json()["data"]
    assert rows["苏州"]["4G"]["outage_count"] == 35 + 8   # 指标随剧本联动

    client.post("/api/scenario/next")                     # 恢复幕
    recovery = client.get("/api/alarms").json()
    assert all(a["status"] == "cleared" for a in recovery["alarms"] if a["type"] == "基站退服")
    client.post("/api/scenario/reset")


# ---------- 告警归并与规则预筛 ----------

def _fake_storm_alarms(count=12, ring="R1"):
    return [{"id": f"A{n}", "city": "苏州", "site": f"S{n}", "tech": "4G",
             "type": "基站退服", "severity": "紧急", "ring": ring, "status": "active"}
            for n in range(count)]


def test_group_events_merges_by_city_and_ring():
    events = dispatch.group_events(_fake_storm_alarms(12))
    assert len(events) == 1 and events[0]["count"] == 12


def test_group_events_ignores_minor_and_cleared():
    alarms = _fake_storm_alarms(2) + [
        {"id": "X", "city": "南京", "site": "N1", "tech": "4G",
         "type": "风扇告警", "severity": "次要", "ring": "", "status": "active"}]
    assert dispatch.group_events(alarms) == []            # 2 站不足成事件，次要告警不参与


def test_prescreen_batch_threshold():
    urgent = dispatch.prescreen({"count": 12})
    assert urgent["priority"] == "紧急" and urgent["deadline_hours"] == 4
    normal = dispatch.prescreen({"count": 5})
    assert normal["priority"] == "重要" and normal["deadline_hours"] == 8


# ---------- 建议单与审批门 ----------

def test_proposal_confirm_creates_ticket(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    created = tickets.create_proposal("苏州|R1", "苏州", "批量退服12站", "定界：传输中断", "紧急", 4)
    assert created["created"]
    result = tickets.confirm_proposal(created["proposal_id"])
    assert result["confirmed"] and result["ticket"]["created"]
    assert tickets.list_tickets()[0]["source"] == "dispatcher"
    again = tickets.confirm_proposal(created["proposal_id"])   # 审批门：不可重复确认
    assert "error" in again


def test_proposal_reject(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    created = tickets.create_proposal("k", "无锡", "s", "d", "重要", 8)
    assert tickets.reject_proposal(created["proposal_id"])["rejected"]
    assert tickets.list_tickets() == []                        # 否决不产生工单


def test_process_alarms_idempotent(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    calls = []
    fake_diagnose = lambda event: calls.append(event) or "假研判：传输中断"
    first = dispatch.process_alarms(_fake_storm_alarms(12), diagnose_fn=fake_diagnose)
    second = dispatch.process_alarms(_fake_storm_alarms(12), diagnose_fn=fake_diagnose)
    assert len(first) == 1 and second == []                    # 同一事件只研判一次
    assert len(calls) == 1
    assert tickets.list_proposals()[0]["status"] == "待确认"
