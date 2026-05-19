import streamlit as st
from openai import OpenAI
import faiss
import numpy as np
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import json

# ✅ 1. 환경 설정
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ 2. 벡터 인덱스 & 메타데이터 로드
index = faiss.read_index("embeddings/sermon_index.faiss")
metadata = np.load("embeddings/sermon_metadata.npy", allow_pickle=True)

# ✅ 3. 검색 함수
def search_similar_docs(query, top_k=5):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # ✅ api_key 추가!
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_vec = np.array(response.data[0].embedding).astype("float32")
    D, I = index.search(np.array([query_vec]), top_k)
    return [metadata[i][1] for i in I[0]]

# ✅ 4. 상담 프롬프트 생성
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

def polish_text(text):
    system_prompt = "너는 신중하고 부드러운 한국어 에디터야. 문장을 자연스럽게 다듬고 어색한 부분은 고쳐줘. 의미는 바꾸지 마."
    user_prompt = f"다음 텍스트를 더 자연스럽고 매끄럽게 정리해줘:\n\n{text}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# ✅ 5. GPT 답변 생성 함수
def get_gpt_response(prompt):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "당신은 신앙 상담가입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# 테스트 질문 답변 엑셀 저장
def save_chat_log_to_excel(user_input, answer, prompt_version="v2"):
    if os.path.exists("version_info.json"):
        with open("version_info.json", "r") as f:
            version = json.load(f).get("embedding_version", "unknown")
    else:
        version = "manual_155_20220411"

    log_dir = f"logs/version_{version}_prompt_{prompt_version}"
    os.makedirs(log_dir, exist_ok=True)

    file_path = os.path.join(log_dir, f"chat_log_{datetime.today().strftime('%Y-%m-%d')}.xlsx")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_log = pd.DataFrame([{
        "시간": timestamp,
        "프롬프트 버전": prompt_version,
        "임베딩 버전": version,
        "질문": user_input,
        "답변": answer
    }])

    if os.path.exists(file_path):
        old_log = pd.read_excel(file_path)
        all_log = pd.concat([old_log, new_log], ignore_index=True)
    else:
        all_log = new_log

    all_log.to_excel(file_path, index=False)

# ✅ 6. Streamlit UI 구성
st.set_page_config(page_title="신앙 상담 챗봇", page_icon="🙏")
st.title("✝️ 신앙 상담 챗봇")
st.write("목사님의 설교 내용을 바탕으로 신앙적인 조언을 드립니다.")

user_input = st.text_input("💬 상담 내용을 입력해주세요:", key="input")

if user_input:
    with st.spinner("말씀에서 답을 찾는 중이예요..."):
        docs = search_similar_docs(user_input)
        prompt = generate_prompt(docs, user_input)
        answer = get_gpt_response(prompt)
        answer = polish_text(answer)  # ✅ 자연스럽게 다듬기!

        st.markdown("---")
        st.markdown(f"**✝️ 상담 답변:**\n\n{answer}")

        save_chat_log_to_excel(user_input, answer, prompt_version="v1")