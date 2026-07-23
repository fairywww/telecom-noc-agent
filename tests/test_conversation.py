"""会话记忆测试：历史组装与滚动摘要压缩（摘要生成被替换，零 LLM 依赖）"""
import conversation
from conversation import 会话


def test_历史组装_交替角色():
    对话 = 会话()
    对话.记录("苏州退服多少？", "58 个。")
    对话.记录("南京呢？", "64 个。")
    片段 = 对话.组装历史()
    assert [条["role"] for 条 in 片段] == ["user", "assistant", "user", "assistant"]
    assert 片段[0]["content"] == "苏州退服多少？"


def test_超出保留轮数_触发压缩(monkeypatch):
    monkeypatch.setattr(conversation, "摘要生成", lambda 原文: "假摘要：谈了苏州与南京的退服")
    对话 = 会话()
    for 序 in range(conversation.保留轮数 + 1):      # 多一轮，触发压缩
        对话.记录(f"问题{序}", f"回答{序}")
    assert len(对话.近期) == conversation.保留轮数    # 近期原文被截断
    assert 对话.摘要.startswith("假摘要")             # 溢出轮次进了摘要
    片段 = 对话.组装历史()
    assert 片段[0]["role"] == "system" and "摘要" in 片段[0]["content"]


def test_未提供会话号_不启用记忆():
    from conversation import 取会话
    assert 取会话("") is None
    assert 取会话(None) is None
