# -*- coding: utf-8 -*-
"""
멀티턴 RAG 회귀 검증.

질문 시퀀스를 차례로 호출하면서 history 를 누적, 각 턴의 답이 직전 흐름을
이어받는지 눈으로 확인한다. (debug_rag.py 는 단일 질문 전용.)

사용법:
    python verify_conversation.py
        → 기본 시나리오(방언 폐지 논점, 사용자 06-24 발견 케이스) 재현.
    python verify_conversation.py "Q1" "Q2" "Q3"
        → 임의 시퀀스 검증.
"""
import sys

import rag

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_QUESTIONS = [
    "방언 기도는 꼭 해야 하나요?",
    "성경에 방언을 폐했다고 나와있지 않나요? 방언을 못하게 하는 교회도 있던데 뭐가 맞는건가요?",
    "고린도전서 13장에 보면 '사랑은 언제까지든지 떨어지지 아니하나 예언도 폐하고 방언도 그치고 지식도 폐하리라 우리가 부분적으로 알고 부분적으로 예언하니 온전한 것이 올 때에는 부분적으로 하던 것이 폐하리라'라고 되어있지 않아?",
]


def run(questions: list[str]) -> None:
    history: list[dict] = []
    for i, q in enumerate(questions, start=1):
        print("=" * 72)
        print(f"[Turn {i}] USER: {q}")
        print("=" * 72)
        answer = rag.answer_question(q, history)
        print(answer)
        print()
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    qs = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_QUESTIONS
    run(qs)
