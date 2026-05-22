# -*- coding: utf-8 -*-
"""
프롬프트 수정 전(OLD) vs 후(NEW) 답변 비교.
모델(gpt-4o)·검색·polish 는 양쪽 동일. 프롬프트 지시문만 차이.
결과: prompt_comparison_<date>.md
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
MODEL = "gpt-4o"

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


def prompt_old(ctx, q):
    return f"""
당신은 신앙 상담가입니다. 사용자의 질문에 대해 아래 설교를 바탕으로 신앙 조언을 해주세요.
설교에 없는 내용은 답하지 말고 목사님께 직접 상담하라고 답하세요.
설교 내용을 참고하자면, 이라고 직접 말할 필요는 없어요.
설교 마지막에 ~~기원합니다, ~~축복합니다와 같은 말은 빼고 답하세요.

[설교 내용]
{ctx}

[사용자 질문]
{q}

[상담 답변]
"""


def prompt_new(ctx, q):
    return f"""당신은 따뜻하고 깊이 있는 목회적 신앙 상담가입니다.
아래 [설교 내용]에 담긴 가르침에 근거하여 사용자의 질문에 답하세요.

- 답변은 반드시 [설교 내용]에 실제로 담긴 내용에 근거해야 합니다.
  설교에 없는 일반적 위로나 세상적 조언을 지어내지 마세요.
- 더 깊은 상담이나 구체적인 인도가 필요한 부분은, 담임 목사님과
  상담하거나 교회를 찾아가도록 자연스럽게 안내해 주세요.
- 단, 신앙의 문제를 세상의 법(법적 근거·법률·법적 지침 등)과 절대
  연관 짓지 마세요. 신앙 상담은 하나님의 뜻과 성경적 원칙에 관한 것이지
  세상 법과는 무관합니다.
- "설교 내용을 참고하자면" 같은 표현은 쓰지 말고, 설교를 자연스럽게 녹여 답하세요.
- "~~기원합니다", "~~축복합니다" 같은 맺음말은 쓰지 마세요.
- 부드럽고 차분한 목회적 어조를 유지하되, 단순한 위로를 넘어
  성경적 원칙에 근거해 답하세요.

[설교 내용]
{ctx}

[사용자 질문]
{q}

[상담 답변]
"""


def answer(prompt_text):
    """app.py 흐름: 답변 생성 -> polish."""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "당신은 신앙 상담가입니다."},
            {"role": "user", "content": prompt_text},
        ],
    )
    raw = r.choices[0].message.content
    p = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "너는 신중하고 부드러운 한국어 에디터야. 문장을 자연스럽게 다듬고 어색한 부분은 고쳐줘. 의미는 바꾸지 마."},
            {"role": "user", "content": f"다음 텍스트를 더 자연스럽고 매끄럽게 정리해줘:\n\n{raw}"},
        ],
    )
    return p.choices[0].message.content.strip()


def main():
    lines = ["# 프롬프트 수정 전(OLD) vs 후(NEW) 비교", ""]
    lines.append(f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- 모델 {MODEL} 고정. 검색·polish 동일. 프롬프트 지시문만 차이.")
    lines.append("")

    for n, q in enumerate(QUESTIONS, 1):
        print(f"=== Q{n}: {q[:30]} ===")
        ctx = "\n---\n".join(retrieve(q))
        print("  OLD ...")
        old = answer(prompt_old(ctx, q))
        print("  NEW ...")
        new = answer(prompt_new(ctx, q))

        lines += [
            f"## Q{n}. {q}", "",
            "### OLD 프롬프트", "", old, "",
            "### NEW 프롬프트", "", new, "",
            "---", "",
        ]

    out = f"prompt_comparison_{datetime.now().strftime('%Y%m%d')}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[OK] 저장: {out}")


if __name__ == "__main__":
    main()
