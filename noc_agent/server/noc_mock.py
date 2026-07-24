"""模拟 NOC 数据源。

真实场景中这个模块不存在——它代表生产上已运行的 NOC 系统，
模仿其两个特征：数据按地市/专业组织、应答带 code/data 信封。
对接真实系统时整体替换为真实地址即可（见 adapter.py 的 NOC_URL）。

启动：python3 -m uvicorn noc_agent.server.noc_mock:app --port 8001
"""
from fastapi import FastAPI

app = FastAPI(title="NOC Mock")

MOCK_ROWS = {
    "南京": {"4G": {"outage_count": 40, "alarm_count": 120}, "5G": {"outage_count": 24, "alarm_count": 86}},
    "苏州": {"4G": {"outage_count": 35, "alarm_count": 95}, "5G": {"outage_count": 23, "alarm_count": 71}},
    "无锡": {"4G": {"outage_count": 19, "alarm_count": 63}, "5G": {"outage_count": 12, "alarm_count": 42}},
}


@app.get("/api/statistics/all")
def statistics_all():
    """NOC 风格接口：按地市/专业给原始数据，用 code/data 信封包装"""
    return {"code": 0, "message": "success", "data": MOCK_ROWS}
