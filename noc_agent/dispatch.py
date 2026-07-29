"""调度器：事件驱动的故障研判与建议单生成。

业务流的自动段「感知 → 研判 → 决策(建议)」在此实现：

  轮询告警 → 归并成事件 → 硬规则预筛(优先级/时限) → Agent 定界研判
          → 写入「待确认」建议单（人工在大屏调度台确认后才成为工单）

设计要点：
  1. 规则与模型分工——批量退服阈值这类白纸黑字的判断用代码写死，
     根因定界这类模糊判断交给 Agent；
  2. 幂等——事件键(event_key)唯一，轮询多少次同一事件只产生一张建议单；
  3. 独立进程——研判耗时数十秒，与毫秒级数据服务隔离部署。

启动：python3 -m noc_agent.dispatch   （需要 8001/8002 在运行）
"""
import os
import time

import requests

NOC_URL = os.environ.get("NOC_URL", "http://localhost:8001")
POLL_SECONDS = 5
OUTAGE_EVENT_MIN_SITES = 3       # 少于 3 站的零星退服不生成建议单，交日常流程

BATCH_OUTAGE_THRESHOLD = 10      # 规范：同一区域 10 站以上为批量退服


def group_events(alarms):
    """把散落的告警归并成事件：同地市+同传输环的退服告警算一个事件。
    这是"告警压缩"的最小实现——调度看事件，不看单条告警。"""
    events = {}
    for alarm in alarms:
        if alarm["type"] != "基站退服" or alarm["status"] != "active":
            continue
        key = f"{alarm['city']}|{alarm.get('ring') or '无环'}"
        event = events.setdefault(key, {
            "event_key": key, "city": alarm["city"], "ring": alarm.get("ring", ""),
            "sites": [], "techs": set(),
        })
        event["sites"].append(alarm["site"])
        event["techs"].add(alarm["tech"])
    for event in events.values():
        event["count"] = len(event["sites"])
        event["techs"] = sorted(event["techs"])
    return [e for e in events.values() if e["count"] >= OUTAGE_EVENT_MIN_SITES]


def prescreen(event):
    """硬规则预筛：确定性的判断不问大模型"""
    if event["count"] >= BATCH_OUTAGE_THRESHOLD:
        return {"priority": "紧急", "deadline_hours": 4,
                "rule": f"批量退服（{event['count']} 站 ≥ {BATCH_OUTAGE_THRESHOLD} 站）"}
    return {"priority": "重要", "deadline_hours": 8,
            "rule": f"区域退服（{event['count']} 站）"}


def diagnose(event):
    """模糊判断交给 Agent：根因定界 + 处置建议（引用规范出处）"""
    from .agent.loop import run_agent
    task = (
        f"告警事件研判：{event['city']}发生基站退服 {event['count']} 站"
        f"（制式：{'/'.join(event['techs'])}），全部位于同一{event['ring'] or '区域'}，"
        f"并伴随该环光路LOS告警。请定界最可能的故障根因（传输/电源/设备/外破），"
        f"给出定界依据与处置建议，引用规范出处，全文不超过 200 字。"
    )
    result = run_agent(task)
    return result.get("answer") or result.get("error", "研判失败")


def process_alarms(alarms, diagnose_fn=diagnose):
    """一次轮询的完整处理。diagnose_fn 可注入，便于无网络测试。"""
    from .storage.tickets import create_proposal, list_proposals

    handled_keys = {p["event_key"] for p in list_proposals(limit=100)}
    created = []
    for event in group_events(alarms):
        if event["event_key"] in handled_keys:
            continue                      # 幂等：同一事件不重复研判
        rule = prescreen(event)
        print(f"[调度器] 发现新事件 {event['event_key']}（{event['count']} 站），"
              f"预筛：{rule['priority']}/{rule['deadline_hours']}h，开始 Agent 研判…")
        diagnosis = diagnose_fn(event)
        summary = (f"{event['city']}批量退服 {event['count']} 站"
                   f"（{'/'.join(event['techs'])}，{event['ring'] or '未关联环'}）；"
                   f"预筛规则：{rule['rule']}")
        result = create_proposal(event["event_key"], event["city"], summary,
                                 diagnosis, rule["priority"], rule["deadline_hours"])
        print(f"[调度器] 建议单已生成：{result}")
        created.append(result)
    return created


def run_forever():
    print(f"调度器启动：每 {POLL_SECONDS}s 轮询 {NOC_URL}/api/alarms")
    while True:
        try:
            alarms = requests.get(f"{NOC_URL}/api/alarms", timeout=5).json()["alarms"]
            process_alarms(alarms)
        except requests.RequestException as exc:
            print(f"[调度器] 轮询失败（{exc}），{POLL_SECONDS}s 后重试")
        except Exception as exc:          # 调度进程不能因单次研判失败而退出
            print(f"[调度器] 处理异常：{exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
