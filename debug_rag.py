# -*- coding: utf-8 -*-
"""
RAG 답변 디버그용 (Supabase match_sermons 스택).

질문 하나에 대해 어떤 설교 청크가 유사도 몇 점으로 매칭되는지 + 최종 답변을
같이 출력해, 답변이 빗나갈 때 원인이
coverage(없음) / retrieval(검색 실패·순위 밀림) / generation(생성 약함)
중 무엇인지 눈으로 판별한다.

사용법:
    python debug_rag.py "헌금을 왜 해야 하나요?"
    python debug_rag.py "헌금을 왜 해야 하나요?" 10      # 상위 N개 확인
"""
import sys

import rag  # 운영과 동일한 클라이언트/RPC/프롬프트 재사용

sys.stdout.reconfigure(encoding="utf-8")


def debug(question: str, match_count: int = 10, preview: int = 200) -> None:
    resp = rag._client.embeddings.create(
        input=question, model="text-embedding-3-small"
    )
    query_vec = resp.data[0].embedding

    result = rag._supabase.rpc(
        "match_sermons",
        {"query_embedding": query_vec, "match_count": match_count},
    ).execute()
    rows = result.data

    print("=" * 72)
    print(f"질문: {question}")
    print(f"match_count={match_count}  (similarity 0~1, 높을수록 유사)")
    print("=" * 72)

    for rank, row in enumerate(rows, start=1):
        src = row.get("video_id", "?")
        sim = row.get("similarity", 0.0)
        snippet = (row.get("content") or "")[:preview].replace("\n", " ")
        print(f"\n[{rank}] sim={sim:.3f}  ── {src}")
        print(f"    {snippet}…")

    print("\n" + "=" * 72)
    print(f"최종 답변 (운영 answer_question, top_k={rag.search_similar_docs.__defaults__[0]})")
    print("=" * 72)
    print(rag.answer_question(question))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용법: python debug_rag.py "질문" [match_count]')
        sys.exit(1)
    q = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    debug(q, match_count=n)
