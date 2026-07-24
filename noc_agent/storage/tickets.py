"""工单存储——系统第一个写操作模块。

SQLite（标准库自带）持久化，两条安全设计：
  1. 幂等保护：同地市已有「待处理」工单时拒绝重复创建，返回已有单号；
  2. 审计字段：每张工单记录创建时间与来源（agent / manual）。
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
