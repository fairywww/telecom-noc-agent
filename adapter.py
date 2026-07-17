"""
文件1：大屏后端（适配层）——「从后端系统取数」就发生在这里
============================================================
它只干一件事：把 NOC 的原始数据，翻译成前端好用的样子。

三步翻译：
  ① 调 NOC 的接口（HTTP 请求，跟浏览器访问网址一回事）
  ② 拆信封、把分散的数字加总（南京4G 40 + 南京5G 24 + ... = 153）
  ③ 换成前端约定的字段名，发出去

启动：python3 -m uvicorn adapter:app --port 8002
"""
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

NOC地址 = "http://localhost:8001"     # 真实场景改成 内网地址（不写进代码库）


@app.get("/api/kpi")
def kpi():
    # ① 取数：向 NOC 后端发 HTTP 请求，拿回 JSON
    应答 = requests.get(f"{NOC地址}/api/statistics/all", timeout=5).json()

    # ② 加工：拆开 {"code":0,"data":...} 信封，把各地市各专业的数字加总
    行 = 应答["data"]
    总退服数 = sum(
        专业数据["outage_count"]
        for 各专业 in 行.values()          # 遍历每个地市
        for 专业数据 in 各专业.values()     # 遍历 4G/5G
    )

    # ③ 应答：用前端约定好的字段名（这就是"契约"）
    return {"outage_total": 总退服数, "city_count": len(行)}


# 顺手托管前端页面（访问 http://localhost:8002/ 就能打开 index.html）
app.mount("/", StaticFiles(directory=str(Path(__file__).parent), html=True))
