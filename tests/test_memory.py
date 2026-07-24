"""会话记忆测试：历史构建、滚动压缩触发、会话获取（摘要函数打桩，零网络依赖）"""
from noc_agent.agent import memory


def test_history_shape():
    session = memory.Session()
    session.recent = [{"user": "问1", "assistant": "答1"}]
    history = session.build_history()
    assert history == [
        {"role": "user", "content": "问1"},
        {"role": "assistant", "content": "答1"},
    ]


def test_summary_prepended():
    session = memory.Session()
    session.summary = "此前讨论了南京退服"
    session.recent = [{"user": "问", "assistant": "答"}]
    history = session.build_history()
    assert history[0]["role"] == "system" and "南京" in history[0]["content"]


def test_compress_triggered_beyond_keep_rounds(monkeypatch):
    calls = []
    monkeypatch.setattr(memory, "summarize", lambda text: calls.append(text) or "假摘要")
    session = memory.Session()
    for i in range(memory.KEEP_ROUNDS + 1):          # 超出保留轮数，应触发一次压缩
        session.record(f"问{i}", f"答{i}")
    assert len(session.recent) == memory.KEEP_ROUNDS
    assert session.summary == "假摘要"
    assert len(calls) == 1 and "问0" in calls[0]     # 被压缩的是最早那轮


def test_get_session():
    assert memory.get_session("") is None
    first = memory.get_session("s1")
    assert memory.get_session("s1") is first          # 同一 id 拿到同一会话
