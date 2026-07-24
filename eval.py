"""Agent 评测：小评测集回归。

LLM 输出有随机性，改一次提示词、换一次模型都可能悄悄破坏原有能力。
评测集就是 Agent 的"回归测试"：固定问题与判定标准，每次改动后重跑，
量化四个指标：成功率、轮数、耗时、词元消耗。

判定方式为关键词包含——粗糙但零成本、无歧义；进阶做法（LLM 当裁判）
留待需要时引入。

运行：python3 eval.py   （需要 8001/8002 两个服务在运行）
"""
import time

from noc_agent.agent.loop import run_agent

EVAL_CASES = [
    {"question": "现在全网退服总数是多少个？", "expect": ["153"]},
    {"question": "哪个地市退服最多？", "expect": ["南京"]},
    {"question": "告警分为哪几个等级？", "expect": ["紧急", "重要", "次要", "提示"]},
    {"question": "按规范，多少个站以上算批量退服？该怎么办？", "expect": ["10", "应急预案"]},
]

if __name__ == "__main__":
    records = []
    for index, case in enumerate(EVAL_CASES, 1):
        started = time.time()
        try:
            result = run_agent(case["question"])
        except Exception as exc:
            result = {"answer": f"[异常] {exc}", "rounds": 0, "tokens": 0}
        elapsed = time.time() - started
        answer = result.get("answer") or ""
        passed = all(keyword in answer for keyword in case["expect"])
        records.append((passed, result.get("rounds", 0), elapsed, result.get("tokens", 0)))
        print(f"[{index}/{len(EVAL_CASES)}] {'通过' if passed else '未通过'} | "
              f"{result.get('rounds', 0)} 轮 | {elapsed:.1f} 秒 | "
              f"{result.get('tokens', 0)} 词元 | {case['question']}")
        if not passed:
            print(f"      缺少关键词：{[k for k in case['expect'] if k not in answer]}")
            print(f"      答案节选：{answer[:120]}")

    passed_count = sum(1 for ok, *_ in records if ok)
    print("\n===== 汇总 =====")
    print(f"成功率：{passed_count}/{len(records)}（{passed_count / len(records):.0%}）")
    print(f"平均轮数：{sum(r for _, r, _, _ in records) / len(records):.1f}")
    print(f"平均耗时：{sum(s for _, _, s, _ in records) / len(records):.1f} 秒")
    print(f"词元合计：{sum(t for _, _, _, t in records)}")
