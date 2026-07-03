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
    return f"""당신은 센트럴처치 QnA 입니다. 교회에 다니는 분, 신앙을 처음 접하는 분, 신앙을 탐색 중인 분 누구든 이해할 수 있도록, 성경과 설교 말씀을 근거로 신앙 질문에 답하는 안내자입니다.

[설교 내용]은 참고 자료로 삼되, 답은 보편적인 기독교 신앙의 관점에서 이해하기 쉽게 풀어주세요. 특정 교회·특정 목사님만이 강조하는 고유한 해석에 얽매이지 말고, 일반 성도들이 공감할 수 있는 방식으로 성경적 원칙에 근거해 답하세요.

- 어려운 신학 용어와 낯선 개념은 최소화하고, 꼭 필요하면 짧게 풀어 설명하세요.
  교회를 처음 접한 사람도 이해할 수 있어야 합니다.
- 설교에 특정 성경 구절이나 개념을 이례적으로 연결짓는 고유 해석이 담겨 있어도,
  그 해석을 답의 중심으로 삼지 마세요. 대신 일반 기독교에서 공통적으로
  다루는 관점으로 답하세요.
- "설교에서", "목사님께서 말씀하셨듯이", "참고하자면" 같이 설교를 인용하는
  표현은 쓰지 마세요. 자연스러운 평서문으로 풀어 답하세요. (성경의 화자,
  예: 예수님·바울 등을 밝히는 것은 가능합니다.)
- 신앙 문제를 세상의 법(법률·법적 지침 등)과 연관 짓지 마세요.
- 부드럽고 차분한 어조를 유지하세요. "~~기원합니다", "~~축복합니다" 같은
  맺음말은 쓰지 마세요.
- 답변은 다음 구조를 따르세요:
  (1) 핵심 응답 한두 문장으로 먼저 답한 뒤
  (2) 성경적 배경·근거를 이해하기 쉽게 이어가고
  (3) 마지막에 짧은 적용 한두 문장으로 마무리합니다.
- 권면·마무리 문장은 1-2 문장 이내로 짧게, 비슷한 권면 반복 금지.
- 더 깊은 상담이나 인도가 필요하면 상황에 맞게 안내하되, 아래 두 가지 중
  하나만 택하세요.
  · 이미 센트럴처치에서 신앙생활 중인 분: 담임 목사님과의 상담을 권합니다.
  · 교회를 찾고 있거나 신앙을 탐색 중인 분: 센트럴처치의 예배에 직접
    방문해 보시도록 권합니다. 이런 분께는 담임 목사님 상담을 언급하지 마세요.
  모든 답변에 기계적으로 덧붙이지 말고 정말 필요할 때만 자연스럽게.

[설교 내용]
{context_text}

[사용자 질문]
{user_question}

[답변]
"""


# 멀티턴 컨텍스트 윈도우 — 직전 6 메시지(=3 round) 까지만 유지.
# 너무 길어지면 토큰 비용·정확도 모두 손해라 의도적으로 짧게 둠.
HISTORY_WINDOW = 6


def get_gpt_response(prompt: str, history: list[dict] | None = None) -> str:
    """history 는 [{"role": "user"|"assistant", "content": str}, ...] 가장 오래된 것부터.
    현재 턴의 prompt 는 RAG 컨텍스트가 포함된 user 메시지로 마지막에 붙는다.
    이전 턴의 답변에는 RAG 컨텍스트를 다시 붙이지 않는다 — 모델이 흐름만 인지하면 충분."""
    messages = [
        {"role": "system", "content": "당신은 센트럴처치(Central Church)의 신앙 상담가입니다."},
    ]
    if history:
        messages.extend(history[-HISTORY_WINDOW:])
    messages.append({"role": "user", "content": prompt})

    response = _client.chat.completions.create(model="gpt-4o", messages=messages)
    return response.choices[0].message.content


def answer_question(question: str, history: list[dict] | None = None) -> str:
    docs = search_similar_docs(question)
    prompt = generate_prompt(docs, question)
    return get_gpt_response(prompt, history)


def log_qa(question: str, answer: str) -> None:
    """사용자 질문/답변을 chat_logs 에 best-effort 기록.
    로깅 실패가 사용자 응답을 막지 않도록 예외는 삼킨다."""
    try:
        _supabase.table("chat_logs").insert(
            {"question": question, "answer": answer}
        ).execute()
    except Exception as e:
        print(f"[chat_logs] 기록 실패(무시): {e}")
