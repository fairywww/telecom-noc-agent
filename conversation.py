"""
文件9：多轮对话与记忆管理
============================================================
接口无状态，"记忆"必须由调用方自己维护。本模块的策略：

  会话记忆 = 更早轮次的滚动摘要 + 最近 N 轮的问答原文

两个关键取舍：
  1. 只保留每轮的「问题 + 最终答案」，工具调用的中间报文一律不留——
     它们体积大、且结论已包含其价值；
  2. 超过保留轮数的旧轮次不丢弃，而是请 LLM 压成摘要（滚动更新），
     关键数字与结论得以延续，token 成本却不随轮数无限增长。

用法（交互式多轮对话）：python3 conversation.py
"""
import sys

from llm import 客户端, 模型名

保留轮数 = 4      # 近期原文保留的轮数，超出部分并入摘要


def 摘要生成(原文):
    """把旧摘要与溢出轮次压缩为一段简短摘要（独立函数，便于测试替换）"""
    应答 = 客户端.chat.completions.create(
        model=模型名,
        messages=[
            {"role": "system", "content": "你是对话摘要器。把给定的运维对话历史压缩为不超过150字的摘要，"
                                          "必须保留：提到的地市、关键数字、已得出的结论。只输出摘要本身。"},
            {"role": "user", "content": 原文},
        ],
        temperature=0.1,
    )
    return (应答.choices[0].message.content or "").strip()


class 会话:
    def __init__(self):
        self.摘要 = ""       # 更早轮次的滚动摘要
        self.近期 = []       # [{"user": 问, "assistant": 答}, ...] 最近几轮原文

    def 组装历史(self):
        """转成可直接拼进 messages 的片段：[摘要(如有)] + 近期各轮 user/assistant"""
        片段 = []
        if self.摘要:
            片段.append({"role": "system", "content": f"（此前对话的摘要）{self.摘要}"})
        for 轮 in self.近期:
            片段.append({"role": "user", "content": 轮["user"]})
            片段.append({"role": "assistant", "content": 轮["assistant"]})
        return 片段

    def 记录(self, 问, 答):
        self.近期.append({"user": 问, "assistant": 答})
        if len(self.近期) > 保留轮数:
            self._压缩()

    def _压缩(self):
        溢出 = self.近期[:-保留轮数]
        self.近期 = self.近期[-保留轮数:]
        原文 = (f"旧摘要：{self.摘要}\n" if self.摘要 else "") + "\n".join(
            f"用户：{轮['user']}\n助手：{轮['assistant']}" for 轮 in 溢出
        )
        self.摘要 = 摘要生成(原文)


# ---- 会话存储：进程内字典（演示用；生产中放 Redis 等外部存储，重启不丢）----

会话表 = {}


def 取会话(session_id):
    if not session_id:
        return None
    return 会话表.setdefault(session_id, 会话())


if __name__ == "__main__":
    from agent import 运行Agent

    会话实例 = 会话()
    print("多轮对话模式（输入 exit 退出）：")
    for 行 in sys.stdin:
        问 = 行.strip()
        if not 问 or 问.lower() == "exit":
            break
        print(f"\n>>> {问}")
        结果 = 运行Agent(问, 打印=True, 历史片段=会话实例.组装历史())
        会话实例.记录(问, 结果["answer"] or "")
