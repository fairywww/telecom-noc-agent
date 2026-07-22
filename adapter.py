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
import json
import os
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# NOC 地址经环境变量注入：本机默认 localhost，Docker 里是服务名，生产是真实系统地址
NOC地址 = os.environ.get("NOC_URL", "http://localhost:8001")


def 全网汇总(行, 字段名):
    """把各地市各专业的某个数字字段全网加总。

    退服、告警乃至以后新增的任何指标，加总逻辑完全相同，
    抽成函数后新增指标只需增加一次调用，不复制循环代码。
    """
    return sum(
        专业数据[字段名]
        for 各专业 in 行.values()          # 遍历每个地市
        for 专业数据 in 各专业.values()     # 遍历 4G/5G
    )


@app.get("/api/kpi")
def kpi():
    # ① 取数：向 NOC 后端发 HTTP 请求，拿回 JSON
    应答 = requests.get(f"{NOC地址}/api/statistics/all", timeout=5).json()

    # ② 加工：拆开 {"code":0,"data":...} 信封，逐项指标加总
    行 = 应答["data"]

    # ③ 应答：用前端约定好的字段名（这就是"契约"）
    return {
        "outage_total": 全网汇总(行, "outage_count"),
        "alarm_total": 全网汇总(行, "alarm_count"),
        "city_count": len(行),
    }


@app.get("/api/city-outage")
def city_outage():
    """明细接口：逐地市给出退服数据（与 /api/kpi 的聚合形态相对）。

    契约设计：各专业的数字放在 by_tech 字典里而不是写死
    outage_4g/outage_5g 字段——将来数据源新增专业（如 700M），
    本接口与前端都无需改动。
    """
    应答 = requests.get(f"{NOC地址}/api/statistics/all", timeout=5).json()
    行 = 应答["data"]

    城市列表 = [
        {
            "city": 地市,
            "by_tech": {专业: 数据["outage_count"] for 专业, 数据 in 各专业.items()},
            "total": sum(数据["outage_count"] for 数据 in 各专业.values()),
        }
        for 地市, 各专业 in 行.items()
    ]
    # 排序放服务端：保证所有使用方看到同一口径（退服多的排前面）
    城市列表.sort(key=lambda 城: 城["total"], reverse=True)
    return {"cities": 城市列表}


@app.get("/api/city-detail")
def city_detail(city: str):
    """单地市完整明细。city 是必填查询参数——缺失时 FastAPI 自动应答 422。

    未知地市不抛异常，而是返回 error + 可选列表：调用方（尤其是 Agent）
    看到错误信息后可以自行纠正。
    """
    应答 = requests.get(f"{NOC地址}/api/statistics/all", timeout=5).json()
    行 = 应答["data"]
    if city not in 行:
        return {"error": f"未知地市：{city}", "可选地市": list(行.keys())}
    各专业 = 行[city]
    return {
        "city": city,
        "by_tech": 各专业,
        "outage_total": sum(数据["outage_count"] for 数据 in 各专业.values()),
        "alarm_total": sum(数据["alarm_count"] for 数据 in 各专业.values()),
    }


class 提问(BaseModel):
    """POST 请求体的契约：Pydantic 负责校验——缺 question 字段直接 422"""
    question: str


@app.post("/api/agent")
def 智能诊断(请求: 提问):
    """把 Agent 包成接口，供大屏对话面板调用。

    演示项目图省事放在大屏后端里；生产中 Agent 应拆成独立服务
    （耗时长、资源占用特性完全不同）。
    """
    from agent import 运行Agent   # 延迟导入：不用 Agent 功能时大屏后端不依赖 LLM 配置
    return 运行Agent(请求.question)


@app.post("/api/agent/stream")
def 智能诊断流(请求: 提问):
    """SSE 版诊断接口：Agent 每产生一个事件（工具调用、答案增量）立即推送。

    SSE（Server-Sent Events）格式约定：每条消息为 "data: <内容>\\n\\n"，
    HTTP 连接保持打开、服务端持续写入——与 LLM 的流式应答同一机制。
    """
    from agent import 运行Agent流

    def 事件流():
        for 事 in 运行Agent流(请求.question):
            yield f"data: {json.dumps(事, ensure_ascii=False)}\n\n"

    return StreamingResponse(事件流(), media_type="text/event-stream")


# 顺手托管前端页面（访问 http://localhost:8002/ 就能打开 index.html）
app.mount("/", StaticFiles(directory=str(Path(__file__).parent), html=True))
