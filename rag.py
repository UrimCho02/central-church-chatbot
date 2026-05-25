import os

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_index = faiss.read_index("embeddings/sermon_index.faiss")
_metadata = np.load("embeddings/sermon_metadata.npy", allow_pickle=True)


def search_similar_docs(query: str, top_k: int = 5) -> list[str]:
    response = _client.embeddings.create(
        input=query,
        model="text-embedding-3-small",
    )
    query_vec = np.array(response.data[0].embedding, dtype="float32")
    _, indices = _index.search(np.array([query_vec]), top_k)
    return [_metadata[i][1] for i in indices[0]]


def generate_prompt(contexts: list[str], user_question: str) -> str:
    context_text = "\n---\n".join(contexts)
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
{context_text}

[사용자 질문]
{user_question}

[상담 답변]
"""


def get_gpt_response(prompt: str) -> str:
    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 신앙 상담가입니다."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def polish_text(text: str) -> str:
    system_prompt = "너는 신중하고 부드러운 한국어 에디터야. 문장을 자연스럽게 다듬고 어색한 부분은 고쳐줘. 의미는 바꾸지 마."
    user_prompt = f"다음 텍스트를 더 자연스럽고 매끄럽게 정리해줘:\n\n{text}"

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def answer_question(question: str) -> str:
    docs = search_similar_docs(question)
    prompt = generate_prompt(docs, question)
    raw_answer = get_gpt_response(prompt)
    return polish_text(raw_answer)
