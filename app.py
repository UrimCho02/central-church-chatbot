import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from rag import answer_question


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


st.set_page_config(page_title="신앙 상담 챗봇", page_icon="🙏")
st.title("✝️ 신앙 상담 챗봇")
st.write("목사님의 설교 내용을 바탕으로 신앙적인 조언을 드립니다.")

user_input = st.text_input("💬 상담 내용을 입력해주세요:", key="input")

if user_input:
    with st.spinner("말씀에서 답을 찾는 중이예요..."):
        answer = answer_question(user_input)

        st.markdown("---")
        st.markdown(f"**✝️ 상담 답변:**\n\n{answer}")

        save_chat_log_to_excel(user_input, answer, prompt_version="v1")
