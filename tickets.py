"""
文件11：工单存储 —— 系统里第一份"写"出来的数据
============================================================
用 SQLite（Python 标准库自带）持久化：进程重启工单不丢。
这是本系统第一个写操作模块，两条安全设计：

  1. 幂等保护：同一地市已有「待处理」工单时拒绝重复创建，
     返回已有工单号——防止 Agent 重复调用刷出一堆重复单；
  2. 审计字段：每张工单记录创建时间与来源（agent / manual）。
"""
import sqlite3
import time
from pathlib import Path

库文件 = Path(__file__).parent / "data" / "tickets.db"


def _连接():
    库文件.parent.mkdir(exist_ok=True)
    连接 = sqlite3.connect(库文件)
    连接.execute("""
        CREATE TABLE IF NOT EXISTS 工单(
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            创建时间  TEXT    NOT NULL,
            地市      TEXT    NOT NULL,
            故障摘要  TEXT    NOT NULL,
            处置建议  TEXT    NOT NULL,
            时限小时  INTEGER NOT NULL,
            状态      TEXT    NOT NULL DEFAULT '待处理',
            来源      TEXT    NOT NULL DEFAULT 'agent'
        )
    """)
    return 连接


def 创建工单(地市, 故障摘要, 处置建议, 时限小时=8, 来源="agent"):
    连接 = _连接()
    try:
        # 幂等保护：同地市存在待处理工单即拒绝，把已有单号告知调用方
        已有 = 连接.execute(
            "SELECT id FROM 工单 WHERE 地市=? AND 状态='待处理'", (地市,)
        ).fetchone()
        if 已有:
            return {"error": f"{地市}已存在待处理工单（编号 {已有[0]}），未重复创建",
                    "已有工单编号": 已有[0]}
        游标 = 连接.execute(
            "INSERT INTO 工单(创建时间, 地市, 故障摘要, 处置建议, 时限小时, 来源) "
            "VALUES(?,?,?,?,?,?)",
            (time.strftime("%Y-%m-%d %H:%M:%S"), 地市, 故障摘要, 处置建议, 时限小时, 来源),
        )
        连接.commit()
        return {"created": True, "工单编号": 游标.lastrowid, "地市": 地市,
                "时限小时": 时限小时, "状态": "待处理"}
    finally:
        连接.close()


def 工单列表(限量=20):
    连接 = _连接()
    try:
        行们 = 连接.execute(
            "SELECT id, 创建时间, 地市, 故障摘要, 处置建议, 时限小时, 状态, 来源 "
            "FROM 工单 ORDER BY id DESC LIMIT ?", (限量,)
        ).fetchall()
        字段 = ["id", "创建时间", "地市", "故障摘要", "处置建议", "时限小时", "状态", "来源"]
        return [dict(zip(字段, 行)) for 行 in 行们]
    finally:
        连接.close()
