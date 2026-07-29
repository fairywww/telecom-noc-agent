"""大屏后端（适配层）：数据接口 / SSE 诊断流 / 工单接口 / 静态托管。

职责：把 NOC 原始数据翻译成前端契约字段；把 Agent 能力包成 HTTP 接口。

启动：python3 -m uvicorn noc_agent.server.adapter:app --port 8002
"""
import json
import os

import requests
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import WEB_DIR

app = FastAPI(title="NOC Dashboard Backend")

# NOC 地址经环境变量注入：本机默认 localhost，Docker 里是服务名，生产是真实系统地址
NOC_URL = os.environ.get("NOC_URL", "http://localhost:8001")


def aggregate(rows, field):
    """把各地市各专业的某个数字字段全网加总（新增指标只需增加一次调用）"""
    return sum(
        tech_data[field]
        for city_data in rows.values()       # 遍历每个地市
        for tech_data in city_data.values()  # 遍历 4G/5G
    )


@app.get("/api/kpi")
def kpi():
    envelope = requests.get(f"{NOC_URL}/api/statistics/all", timeout=5).json()
    rows = envelope["data"]
    return {
        "outage_total": aggregate(rows, "outage_count"),
        "alarm_total": aggregate(rows, "alarm_count"),
        "city_count": len(rows),
    }


@app.get("/api/city-outage")
def city_outage():
    """明细接口：逐地市退服数据。by_tech 用字典承载——新增专业时契约零改动。"""
    envelope = requests.get(f"{NOC_URL}/api/statistics/all", timeout=5).json()
    rows = envelope["data"]
    cities = [
        {
            "city": city,
            "by_tech": {tech: data["outage_count"] for tech, data in city_data.items()},
            "total": sum(data["outage_count"] for data in city_data.values()),
        }
        for city, city_data in rows.items()
    ]
    # 排序放服务端：保证所有使用方看到同一口径（退服多的排前面）
    cities.sort(key=lambda c: c["total"], reverse=True)
    return {"cities": cities}


@app.get("/api/city-detail")
def city_detail(city: str):
    """单地市完整明细。未知地市返回可自纠错误（error + 可选列表）。"""
    envelope = requests.get(f"{NOC_URL}/api/statistics/all", timeout=5).json()
    rows = envelope["data"]
    if city not in rows:
        return {"error": f"未知地市：{city}", "available_cities": list(rows.keys())}
    city_data = rows[city]
    return {
        "city": city,
        "by_tech": city_data,
        "outage_total": sum(d["outage_count"] for d in city_data.values()),
        "alarm_total": sum(d["alarm_count"] for d in city_data.values()),
    }


class TicketRequest(BaseModel):
    city: str
    summary: str
    action: str
    deadline_hours: int = 8


@app.post("/api/tickets")
def create_ticket_endpoint(request: TicketRequest):
    """创建处置工单（写操作）。幂等保护在存储层：同地市已有待处理工单则拒绝。"""
    from ..storage.tickets import create_ticket
    return create_ticket(request.city, request.summary, request.action, request.deadline_hours)


@app.get("/api/tickets")
def list_tickets_endpoint():
    from ..storage.tickets import list_tickets
    return {"tickets": list_tickets()}


@app.get("/api/proposals")
def list_proposals_endpoint():
    from ..storage.tickets import list_proposals
    return {"proposals": list_proposals()}


@app.post("/api/proposals/{proposal_id}/confirm")
def confirm_proposal_endpoint(proposal_id: int):
    """审批门：人工确认后建议单才转为正式工单"""
    from ..storage.tickets import confirm_proposal
    return confirm_proposal(proposal_id)


@app.post("/api/proposals/{proposal_id}/reject")
def reject_proposal_endpoint(proposal_id: int):
    from ..storage.tickets import reject_proposal
    return reject_proposal(proposal_id)


@app.get("/api/scenario")
def scenario_state():
    """演示剧本状态与控制：前端遥控按钮经此代理到数据源（同源免跨域）"""
    return requests.get(f"{NOC_URL}/api/scenario", timeout=5).json()


@app.post("/api/scenario/next")
def scenario_next():
    return requests.post(f"{NOC_URL}/api/scenario/next", timeout=5).json()


@app.post("/api/scenario/reset")
def scenario_reset():
    return requests.post(f"{NOC_URL}/api/scenario/reset", timeout=5).json()


class AskRequest(BaseModel):
    question: str
    session_id: str = ""    # 可选会话号；带上即启用多轮对话记忆


@app.post("/api/agent")
def ask_agent(request: AskRequest):
    """非流式诊断接口。演示项目挂在大屏后端进程内；生产中 Agent 应拆独立服务。"""
    from ..agent.loop import run_agent
    return run_agent(request.question)


@app.post("/api/agent/stream")
def ask_agent_stream(request: AskRequest):
    """SSE 诊断接口：每个事件（工具调用、答案增量）即时推送。"""
    from ..agent.loop import run_agent_stream
    from ..agent.memory import get_session

    session = get_session(request.session_id)

    def event_stream():
        answer_parts = []
        history = session.build_history() if session else None
        for event in run_agent_stream(request.question, history=history):
            if event["event"] == "text":
                answer_parts.append(event["text"])
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        if session and answer_parts:          # 只记结论，不记工具中间量
            session.record(request.question, "".join(answer_parts))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 托管前端页面（须在全部 API 路由之后：mount("/") 会兜住所有路径）
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True))
