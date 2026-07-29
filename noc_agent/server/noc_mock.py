"""模拟 NOC 数据源 + 演示剧本引擎。

真实场景中本模块不存在——它代表生产上已运行的 NOC 系统。除提供
指标快照外，v1.5 起它还是一台"故障演播机"：内置三幕演示剧本，
数据随剧本推进，供调度闭环演示与开发联调使用。

  第 0 幕 normal    平稳态：基线指标 + 两条次要告警
  第 1 幕 storm     突发：苏州传输环中断，12 站批量退服，告警成串
  第 2 幕 recovery  恢复：告警清除，指标回落

导演遥控器：POST /api/scenario/next 推进下一幕；POST /api/scenario/reset 回到第 0 幕。

启动：python3 -m uvicorn noc_agent.server.noc_mock:app --port 8001
"""
import copy
import time

from fastapi import FastAPI

app = FastAPI(title="NOC Mock & Scenario Engine")

BASE_ROWS = {
    "南京": {"4G": {"outage_count": 40, "alarm_count": 120}, "5G": {"outage_count": 24, "alarm_count": 86}},
    "苏州": {"4G": {"outage_count": 35, "alarm_count": 95}, "5G": {"outage_count": 23, "alarm_count": 71}},
    "无锡": {"4G": {"outage_count": 19, "alarm_count": 63}, "5G": {"outage_count": 12, "alarm_count": 42}},
}

# ---------- 剧本定义 ----------

STORM_RING = "传输环 RING-SZ-03"
STORM_SITES = [f"SZ-{n:04d}" for n in range(1, 13)]      # 12 站，超过批量退服阈值(10)

NORMAL_ALARMS = [
    {"id": "ALM-N01", "city": "南京", "site": "NJ-0207", "tech": "4G",
     "type": "风扇告警", "severity": "次要", "ring": "", "status": "active"},
    {"id": "ALM-N02", "city": "无锡", "site": "WX-0113", "tech": "5G",
     "type": "电池老化", "severity": "次要", "ring": "", "status": "active"},
]


def _storm_alarms():
    alarms = [
        {"id": "ALM-S000", "city": "苏州", "site": "SZ-RING", "tech": "传输",
         "type": "光路LOS", "severity": "紧急", "ring": STORM_RING, "status": "active"},
    ]
    for n, site in enumerate(STORM_SITES, 1):
        alarms.append({
            "id": f"ALM-S{n:03d}", "city": "苏州", "site": site,
            "tech": "4G" if n % 3 else "5G", "type": "基站退服",
            "severity": "紧急", "ring": STORM_RING, "status": "active",
        })
    return alarms


ACTS = [
    {"name": "normal", "title": "第0幕·平稳态"},
    {"name": "storm", "title": "第1幕·苏州传输环中断（批量退服）"},
    {"name": "recovery", "title": "第2幕·抢通恢复"},
]

_state = {"index": 0, "since": time.strftime("%H:%M:%S")}


def _current_act():
    return ACTS[_state["index"]]


def _current_rows():
    """指标快照随剧本变化：风暴幕苏州退服 +12（4G+8 / 5G+4）、告警上翻"""
    rows = copy.deepcopy(BASE_ROWS)
    if _current_act()["name"] == "storm":
        rows["苏州"]["4G"]["outage_count"] += 8
        rows["苏州"]["4G"]["alarm_count"] += 26
        rows["苏州"]["5G"]["outage_count"] += 4
        rows["苏州"]["5G"]["alarm_count"] += 14
    return rows


def _current_alarms():
    act = _current_act()["name"]
    if act == "storm":
        return NORMAL_ALARMS + _storm_alarms()
    if act == "recovery":
        return NORMAL_ALARMS + [dict(a, status="cleared") for a in _storm_alarms()]
    return list(NORMAL_ALARMS)


# ---------- 接口 ----------

@app.get("/api/statistics/all")
def statistics_all():
    """NOC 风格接口：按地市/专业给原始数据，用 code/data 信封包装"""
    return {"code": 0, "message": "success", "data": _current_rows()}


@app.get("/api/alarms")
def alarms():
    """告警事件流：调度器的感知输入"""
    return {"act": _current_act(), "alarms": _current_alarms()}


@app.get("/api/scenario")
def scenario():
    return {"act": _current_act(), "index": _state["index"], "since": _state["since"]}


@app.post("/api/scenario/next")
def scenario_next():
    _state["index"] = (_state["index"] + 1) % len(ACTS)
    _state["since"] = time.strftime("%H:%M:%S")
    return scenario()


@app.post("/api/scenario/reset")
def scenario_reset():
    _state["index"] = 0
    _state["since"] = time.strftime("%H:%M:%S")
    return scenario()
