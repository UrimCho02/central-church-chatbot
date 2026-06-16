import os

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)


def search_similar_docs(query: str, top_k: int = 5) -> list[str]:
    response = _client.embeddings.create(
        input=query,
        model="text-embedding-3-small",
    )
    query_vec = response.data[0].embedding
    result = _supabase.rpc(
        "match_sermons",
        {"query_embedding": query_vec, "match_count": top_k},
    ).execute()
    return [row["content"] for row in result.data]


def generate_prompt(contexts: list[str], user_question: str) -> str:
    context_text = "\n---\n".join(contexts)
    return f"""당신은 센트럴처치(Central Church)의 따뜻하고 깊이 있는 목회적 신앙 상담가입니다.
아래 [설교 내용]은 센트럴처치 담임 목사님의 설교 말씀이며, 이 가르침에 근거하여 사용자의 질문에 답하세요.

- 답변은 반드시 [설교 내용]에 실제로 담긴 내용에 근거해야 합니다.
  설교에 없는 일반적 위로나 세상적 조언을 지어내지 마세요.
- 더 깊은 상담이나 인도가 필요한 부분은 질문자의 상황에 맞게 안내하되, 아래 두 가지를
  절대 함께 권하지 말고 상황에 맞는 하나만 택하세요.
  · 이미 센트럴처치에서 신앙생활 중인 분: 담임 목사님과의 상담을 권합니다.
  · 교회를 찾고 있거나 신앙을 탐색 중인 분: 센트럴처치의 설교 말씀을 더 들어보시고
    예배에 직접 방문해 보시도록 권합니다. 이런 분은 아직 담임 목사님이 안 계시므로
    담임 목사님과의 상담은 절대 언급하지 마세요.
  단, 모든 답변에 기계적으로 덧붙이지 말고 정말 필요할 때만 자연스럽게 안내하세요.
- 단, 신앙의 문제를 세상의 법(법적 근거·법률·법적 지침 등)과 절대
  연관 짓지 마세요. 신앙 상담은 하나님의 뜻과 성경적 원칙에 관한 것이지
  세상 법과는 무관합니다.
- "설교 내용을 참고하자면" 같은 표현은 쓰지 말고, 설교를 자연스럽게 녹여 답하세요.
- "~~기원합니다", "~~축복합니다" 같은 맺음말은 쓰지 마세요.
- 부드럽고 차분한 목회적 어조를 유지하되, 단순한 위로를 넘어
  성경적 원칙에 근거해 답하세요.
- 답변은 다음 구조를 따르세요:
  (1) 핵심 응답 한두 문장으로 먼저 답한 뒤
  (2) 설교 말씀에 근거한 풀이를 이어가고
  (3) 마지막에 짧은 적용 한두 문장으로 마무리합니다.
- 권면·마무리 문장은 1-2 문장 이내로 짧게 끝내고,
  비슷한 권면을 반복하지 마세요.

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
            {"role": "system", "content": "당신은 센트럴처치(Central Church)의 신앙 상담가입니다."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def answer_question(question: str) -> str:
    docs = search_similar_docs(question)
    prompt = generate_prompt(docs, question)
    return get_gpt_response(prompt)


def log_qa(question: str, answer: str) -> None:
    """사용자 질문/답변을 chat_logs 에 best-effort 기록.
    로깅 실패가 사용자 응답을 막지 않도록 예외는 삼킨다."""
    try:
        _supabase.table("chat_logs").insert(
            {"question": question, "answer": answer}
        ).execute()
    except Exception as e:
        print(f"[chat_logs] 기록 실패(무시): {e}")
