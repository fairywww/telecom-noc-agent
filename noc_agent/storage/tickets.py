"""工单与研判建议单存储——系统的写操作模块。

SQLite（标准库自带）持久化，安全设计：
  1. 幂等保护：同地市已有「待处理」工单时拒绝重复创建；同一事件键
     （event_key）只生成一张建议单——调度器轮询不会刷重复建议；
  2. 审批门落在数据模型上：调度器只能写「待确认」的建议单（proposal），
     人工确认后才转为正式工单（ticket）；
  3. 审计字段：创建时间与来源全程留痕。
"""
import sqlite3
import time

from ..config import TICKET_DB

DB_PATH = TICKET_DB


def _connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets(
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at     TEXT    NOT NULL,
            city           TEXT    NOT NULL,
            summary        TEXT    NOT NULL,
            action         TEXT    NOT NULL,
            deadline_hours INTEGER NOT NULL,
            status         TEXT    NOT NULL DEFAULT '待处理',
            source         TEXT    NOT NULL DEFAULT 'agent'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proposals(
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at     TEXT    NOT NULL,
            event_key      TEXT    NOT NULL UNIQUE,
            city           TEXT    NOT NULL,
            summary        TEXT    NOT NULL,
            diagnosis      TEXT    NOT NULL,
            priority       TEXT    NOT NULL,
            deadline_hours INTEGER NOT NULL,
            status         TEXT    NOT NULL DEFAULT '待确认',
            ticket_id      INTEGER
        )
    """)
    return conn


def create_ticket(city, summary, action, deadline_hours=8, source="agent"):
    conn = _connect()
    try:
        # 幂等保护：同地市存在待处理工单即拒绝，把已有单号告知调用方
        existing = conn.execute(
            "SELECT id FROM tickets WHERE city=? AND status='待处理'", (city,)
        ).fetchone()
        if existing:
            return {"error": f"{city}已存在待处理工单（编号 {existing[0]}），未重复创建",
                    "existing_ticket_id": existing[0]}
        cursor = conn.execute(
            "INSERT INTO tickets(created_at, city, summary, action, deadline_hours, source) "
            "VALUES(?,?,?,?,?,?)",
            (time.strftime("%Y-%m-%d %H:%M:%S"), city, summary, action, deadline_hours, source),
        )
        conn.commit()
        return {"created": True, "ticket_id": cursor.lastrowid, "city": city,
                "deadline_hours": deadline_hours, "status": "待处理"}
    finally:
        conn.close()


def create_proposal(event_key, city, summary, diagnosis, priority, deadline_hours):
    """写入一张「待确认」研判建议单。同一事件键只写一次（幂等）。"""
    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT id FROM proposals WHERE event_key=?", (event_key,)).fetchone()
        if existing:
            return {"error": "该事件已有建议单", "existing_proposal_id": existing[0]}
        cursor = conn.execute(
            "INSERT INTO proposals(created_at, event_key, city, summary, diagnosis, "
            "priority, deadline_hours) VALUES(?,?,?,?,?,?,?)",
            (time.strftime("%Y-%m-%d %H:%M:%S"), event_key, city, summary,
             diagnosis, priority, deadline_hours),
        )
        conn.commit()
        return {"created": True, "proposal_id": cursor.lastrowid}
    finally:
        conn.close()


def list_proposals(limit=20):
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, created_at, event_key, city, summary, diagnosis, priority, "
            "deadline_hours, status, ticket_id FROM proposals ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
        fields = ["id", "created_at", "event_key", "city", "summary", "diagnosis",
                  "priority", "deadline_hours", "status", "ticket_id"]
        return [dict(zip(fields, row)) for row in rows]
    finally:
        conn.close()


def confirm_proposal(proposal_id):
    """人工确认：建议单转正式工单（审批门的落地动作）"""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT city, summary, diagnosis, deadline_hours, status FROM proposals WHERE id=?",
            (proposal_id,)).fetchone()
        if not row:
            return {"error": f"建议单 {proposal_id} 不存在"}
        city, summary, diagnosis, deadline_hours, status = row
        if status != "待确认":
            return {"error": f"建议单 {proposal_id} 当前状态为「{status}」，不可重复处理"}
    finally:
        conn.close()

    ticket = create_ticket(city, summary, diagnosis, deadline_hours, source="dispatcher")
    conn = _connect()
    try:
        if ticket.get("created"):
            conn.execute("UPDATE proposals SET status='已确认', ticket_id=? WHERE id=?",
                         (ticket["ticket_id"], proposal_id))
        else:
            conn.execute("UPDATE proposals SET status='已确认', ticket_id=? WHERE id=?",
                         (ticket.get("existing_ticket_id"), proposal_id))
        conn.commit()
        return {"confirmed": True, "proposal_id": proposal_id, "ticket": ticket}
    finally:
        conn.close()


def reject_proposal(proposal_id):
    conn = _connect()
    try:
        updated = conn.execute(
            "UPDATE proposals SET status='已否决' WHERE id=? AND status='待确认'",
            (proposal_id,)).rowcount
        conn.commit()
        if not updated:
            return {"error": f"建议单 {proposal_id} 不存在或已处理"}
        return {"rejected": True, "proposal_id": proposal_id}
    finally:
        conn.close()


def list_tickets(limit=20):
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, created_at, city, summary, action, deadline_hours, status, source "
            "FROM tickets ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        fields = ["id", "created_at", "city", "summary", "action",
                  "deadline_hours", "status", "source"]
        return [dict(zip(fields, row)) for row in rows]
    finally:
        conn.close()
