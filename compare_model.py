# -*- coding: utf-8 -*-
"""
gpt-4 vs gpt-4o 답변 비교 테스트.

검색(corrected_transcripts 기반 새 인덱스)은 양쪽 동일하게 두고,
답변 생성 + polish 단계만 모델을 바꿔 app.py 흐름 그대로 비교한다.
결과: model_comparison_<date>.md
"""
import sys
from datetime import datetime
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
client = OpenAI()

QUESTIONS = [
    "목사님이 마음에 안 들어요",
    "십일조를 꼭 해야 되나요?",
    "세상이 점점 이상해지는것 같아요. 크리스챤으로써 어떻게 살아가야 하나요?",
    "주일 성수를 꼭 해야하나요?",
    "회사가 어려워서 임원감축을 해야 하는데 나는 대상이 아니야. "
    "우리 팀원들 절반이 나갈것 같은데 내가 대신 나가는거 신앙적으로 옳은 판단일까?",
]

index = faiss.read_index("embeddings/sermon_index.faiss")
metadata = np.load("embeddings/sermon_metadata.npy", allow_pickle=True)


def retrieve(query, top_k=5):
    r = client.embeddings.create(input=query, model="text-embedding-3-small")
    qv = np.array(r.data[0].embedding).astype("float32")
    D, I = index.search(np.array([qv]), top_k)
    return [metadata[i][1] for i in I[0]]


def generate_prompt(contexts, q):
    ctx = "\n---\n".join(contexts)
    return f"""당신은 신앙 상담가입니다. 사용자의 질문에 대해 아래 설교를 바탕으로 신앙 조언을 해주세요.
설교에 없는 내용은 답하지 말고 목사님께 직접 상담하라고 답하세요.
설교 내용을 참고하자면, 이라고 직접 말할 필요는 없어요.
설교 마지막에 ~~기원합니다, ~~축복합니다와 같은 말은 빼고 답하세요.

[설교 내용]
{ctx}

[사용자 질문]
{q}

[상담 답변]
"""


def answer(model, contexts, q):
    """app.py 흐름: 답변 생성 -> polish. 둘 다 같은 model 사용."""
    r = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 신앙 상담가입니다."},
            {"role": "user", "content": generate_prompt(contexts, q)},
        ],
    )
    raw = r.choices[0].message.content
    p = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "너는 신중하고 부드러운 한국어 에디터야. 문장을 자연스럽게 다듬고 어색한 부분은 고쳐줘. 의미는 바꾸지 마."},
            {"role": "user", "content": f"다음 텍스트를 더 자연스럽고 매끄럽게 정리해줘:\n\n{raw}"},
        ],
    )
    return p.choices[0].message.content.strip()


def main():
    lines = ["# gpt-4 vs gpt-4o 답변 비교", ""]
    lines.append(f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("- 검색은 양쪽 동일(corrected 인덱스, top-5). 답변+polish 단계만 모델 차이.")
    lines.append("")

    for n, q in enumerate(QUESTIONS, 1):
        print(f"=== Q{n}: {q[:30]} ===")
        ctx = retrieve(q)
        print("  gpt-4 ...")
        a4 = answer("gpt-4", ctx, q)
        print("  gpt-4o ...")
        a4o = answer("gpt-4o", ctx, q)

        lines.append(f"## Q{n}. {q}")
        lines.append("")
        lines.append("### gpt-4 (현재 app.py)")
        lines.append("")
        lines.append(a4)
        lines.append("")
        lines.append("### gpt-4o (교체 후보)")
        lines.append("")
        lines.append(a4o)
        lines.append("")
        lines.append("---")
        lines.append("")

    out = f"model_comparison_{datetime.now().strftime('%Y%m%d')}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[OK] 저장: {out}")


if __name__ == "__main__":
    main()
