"""多轮对话与记忆管理。

接口无状态，"记忆"由调用方维护：

  会话记忆 = 更早轮次的滚动摘要 + 最近 N 轮的问答原文

两个关键取舍：
  1. 只保留每轮的「问题 + 最终答案」，工具调用中间报文不留——
     体积大、价值已凝结在答案里、实时数据会过期；
  2. 超出保留轮数的旧轮次压成摘要滚动更新，token 成本有界。

用法（交互式多轮对话）：python3 -m noc_agent.agent.memory
"""
import sys

from ..llm import MODEL, client

KEEP_ROUNDS = 4      # 近期原文保留的轮数，超出部分并入摘要


def summarize(text):
    """把旧摘要与溢出轮次压缩为一段简短摘要（独立函数，便于测试替换）"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是对话摘要器。把给定的运维对话历史压缩为不超过150字的摘要，"
                                          "必须保留：提到的地市、关键数字、已得出的结论。只输出摘要本身。"},
            {"role": "user", "content": text},
        ],
        temperature=0.1,
    )
    return (response.choices[0].message.content or "").strip()


class Session:
    def __init__(self):
        self.summary = ""     # 更早轮次的滚动摘要
        self.recent = []      # [{"user": 问, "assistant": 答}, ...] 最近几轮原文

    def build_history(self):
        """转成可直接拼进 messages 的片段：[摘要(如有)] + 近期各轮 user/assistant"""
        history = []
        if self.summary:
            history.append({"role": "system", "content": f"（此前对话的摘要）{self.summary}"})
        for turn in self.recent:
            history.append({"role": "user", "content": turn["user"]})
            history.append({"role": "assistant", "content": turn["assistant"]})
        return history

    def record(self, question, answer):
        self.recent.append({"user": question, "assistant": answer})
        if len(self.recent) > KEEP_ROUNDS:
            self._compress()

    def _compress(self):
        overflow = self.recent[:-KEEP_ROUNDS]
        self.recent = self.recent[-KEEP_ROUNDS:]
        text = (f"旧摘要：{self.summary}\n" if self.summary else "") + "\n".join(
            f"用户：{turn['user']}\n助手：{turn['assistant']}" for turn in overflow
        )
        self.summary = summarize(text)


# ---- 会话存储：进程内字典（演示用；生产应放 Redis 等外部存储）----

SESSIONS = {}


def get_session(session_id):
    if not session_id:
        return None
    return SESSIONS.setdefault(session_id, Session())


if __name__ == "__main__":
    from .loop import run_agent

    session = Session()
    print("多轮对话模式（输入 exit 退出）：")
    for line in sys.stdin:
        question = line.strip()
        if not question or question.lower() == "exit":
            break
        print(f"\n>>> {question}")
        result = run_agent(question, verbose=True, history=session.build_history())
        session.record(question, result["answer"] or "")
