# -*- coding: utf-8 -*-
"""
3년 필터 적용(A) vs 미적용(B) 응답 비교 테스트.

A: embeddings/sermon_index.faiss        (155개, 최근 3년)
B: embeddings/sermon_index_full.faiss   (263개, 전체)

각 테스트 질문에 대해 양쪽 인덱스로 검색 -> 답변 생성 -> polish 까지
app.py 와 동일한 흐름으로 처리하고, 결과를 filter_comparison_<date>.md 로 저장한다.
"""
import os
import sys
from datetime import datetime
from openai import OpenAI
import faiss
import numpy as np
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 과거 logs/ 에서 추출한 테스트 질문 5개
QUESTIONS = [
    "목사님이 마음에 안 들어요",
    "십일조를 꼭 해야 되나요?",
    "세상이 점점 이상해지는것 같아요. 크리스챤으로써 어떻게 살아가야 하나요?",
    "주일 성수를 꼭 해야하나요?",
    "회사가 어려워서 임원감축을 해야 하는데 나는 대상이 아니야. "
    "우리 팀원들 절반이 나갈것 같은데 내가 대신 나가는거 신앙적으로 옳은 판단일까?",
]


def embed_query(query):
    r = client.embeddings.create(input=query, model="text-embedding-3-small")
    return np.array(r.data[0].embedding).astype("float32")


def search(index, metadata, query_vec, top_k=5):
    D, I = index.search(np.array([query_vec]), top_k)
    return [(metadata[i][0], metadata[i][1]) for i in I[0]]  # (파일명, 청크)


# app.py 의 generate_prompt 와 동일
def generate_prompt(contexts, user_question):
    context_text = "\n---\n".join(contexts)
    return f"""
당신은 신앙 상담가입니다. 사용자의 질문에 대해 아래 설교를 바탕으로 신앙 조언을 해주세요.
설교에 없는 내용은 답하지 말고 목사님께 직접 상담하라고 답하세요.
설교 내용을 참고하자면, 이라고 직접 말할 필요는 없어요.
설교 마지막에 ~~기원합니다, ~~축복합니다와 같은 말은 빼고 답하세요.

[설교 내용]
{context_text}

[사용자 질문]
{user_question}

[상담 답변]
"""


def get_gpt_response(prompt):
    r = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "당신은 신앙 상담가입니다."},
            {"role": "user", "content": prompt},
        ],
    )
    return r.choices[0].message.content


def polish_text(text):
    r = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "너는 신중하고 부드러운 한국어 에디터야. 문장을 자연스럽게 다듬고 어색한 부분은 고쳐줘. 의미는 바꾸지 마."},
            {"role": "user", "content": f"다음 텍스트를 더 자연스럽고 매끄럽게 정리해줘:\n\n{text}"},
        ],
    )
    return r.choices[0].message.content.strip()


def answer(index, metadata, query):
    """검색 -> 답변 -> polish. (답변, 검색된 파일명 리스트) 반환."""
    qv = embed_query(query)
    hits = search(index, metadata, qv)
    files = [f for f, _ in hits]
    chunks = [c for _, c in hits]
    raw = get_gpt_response(generate_prompt(chunks, query))
    return polish_text(raw), files


def main():
    idx_a = faiss.read_index("embeddings/sermon_index.faiss")
    meta_a = np.load("embeddings/sermon_metadata.npy", allow_pickle=True)
    idx_b = faiss.read_index("embeddings/sermon_index_full.faiss")
    meta_b = np.load("embeddings/sermon_metadata_full.npy", allow_pickle=True)

    print(f"A(필터 적용) 청크 {idx_a.ntotal}개 / B(전체) 청크 {idx_b.ntotal}개")

    lines = []
    lines.append("# 3년 필터 적용 vs 미적용 응답 비교")
    lines.append("")
    lines.append(f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- **A안 (필터 적용)**: 청크 {idx_a.ntotal}개 — 최근 3년 설교만")
    lines.append(f"- **B안 (필터 미적용)**: 청크 {idx_b.ntotal}개 — 전체 설교")
    lines.append("- 각 답변은 app.py 와 동일하게 검색 top-5 → GPT-4 → polish 까지 거침")
    lines.append("")

    for n, q in enumerate(QUESTIONS, 1):
        print(f"\n=== Q{n}: {q[:40]} ===")
        print("  A안 처리 중...")
        ans_a, files_a = answer(idx_a, meta_a, q)
        print("  B안 처리 중...")
        ans_b, files_b = answer(idx_b, meta_b, q)

        only_b = [f for f in files_b if f not in files_a]

        lines.append(f"## Q{n}. {q}")
        lines.append("")
        lines.append("### A안 (필터 적용, 155개)")
        lines.append("**검색된 설교:**")
        for f in files_a:
            lines.append(f"- {f}")
        lines.append("")
        lines.append("**답변:**")
        lines.append("")
        lines.append(ans_a)
        lines.append("")
        lines.append("### B안 (필터 미적용, 263개)")
        lines.append("**검색된 설교:**")
        for f in files_b:
            mark = "  ⬅️ A안엔 없던 설교" if f in only_b else ""
            lines.append(f"- {f}{mark}")
        lines.append("")
        lines.append("**답변:**")
        lines.append("")
        lines.append(ans_b)
        lines.append("")
        lines.append("---")
        lines.append("")

    out = f"filter_comparison_{datetime.now().strftime('%Y%m%d')}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n[OK] 비교 결과 저장: {out}")


if __name__ == "__main__":
    main()
