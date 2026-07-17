"""
文件0：迷你 NOC 后端（替身）
============================================================
真实场景里这个文件【不存在也不用写】——它代表已经在生产上跑着的
生产 NOC 系统。这里用 20 行代码模仿它，只为了让教程能在本机跑通。

它模仿了 生产 NOC 系统的两个特征：
  1. 数据按地市/专业分开存（就像数据库里的行）
  2. 应答用 {"code":0, "data":...} 信封包着（生产系统常见的统一应答格式）

启动：python3 -m uvicorn noc_backend:app --port 8001
"""
from fastapi import FastAPI

app = FastAPI()

# 假装这是数据库里查出来的行（真实 NOC 里这些来自 PostgreSQL）
数据库里的行 = {
    "南京": {"4G": {"outage_count": 40}, "5G": {"outage_count": 24}},
    "苏州": {"4G": {"outage_count": 35}, "5G": {"outage_count": 23}},
    "无锡": {"4G": {"outage_count": 19}, "5G": {"outage_count": 12}},
}


@app.get("/api/statistics/all")
def statistics_all():
    """NOC 风格的接口：按地市/专业给原始数据，用 code/data 信封包装"""
    return {"code": 0, "message": "success", "data": 数据库里的行}
