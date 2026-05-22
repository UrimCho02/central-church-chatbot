import os
import re
import sys
from openai import OpenAI
import faiss
import numpy as np
from dotenv import load_dotenv
from datetime import datetime
import json

sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 출력 깨짐/크래시 방지

# 📌 1. API 키 로드
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 📌 2. 폴더 경로
input_folder = "corrected_transcripts"  # LLM 교정본 사용
embedding_model = "text-embedding-3-small"  # 또는 text-embedding-ada-002

# 📌 3. 텍스트 임베딩 함수
def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# 📌 4. 날짜 기반 정렬 함수
def extract_date(filename):
    match = re.search(r"20\d{6}", filename)
    if match:
        return datetime.strptime(match.group(), "%Y%m%d")
    return datetime.min  # 날짜가 없으면 가장 오래된 것으로 처리

# 📌 5. 전체 설교 선택 (3년 필터 미적용 — 비교 테스트 결과 B안 채택)
# 오래된 설교에만 있는 주제(십일조 등)의 누락을 막기 위해 전체를 임베딩한다.
all_files = [f for f in os.listdir(input_folder) if f.endswith(".txt")]
selected_files = sorted(all_files, key=extract_date, reverse=True)
version = f"{len(selected_files)}_{extract_date(selected_files[-1]).strftime('%Y%m%d')}"


# 📌 6. 텍스트 로딩 + 나누기
documents = []
texts = []

for file in selected_files:
    with open(os.path.join(input_folder, file), "r", encoding="utf-8") as f:
        content = f.read()
        documents.append((file, content))

        # 긴 텍스트는 나누어서 처리
        chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
        for chunk in chunks:
            texts.append((file, chunk))

# 📌 7. 임베딩 추출
embeddings = []
metadata = []

for idx, (filename, chunk) in enumerate(texts):
    print(f"[{idx+1}/{len(texts)}] {filename} 임베딩 중...")
    embedding = get_embedding(chunk)
    embeddings.append(embedding)
    metadata.append((filename, chunk))

# 📌 8. FAISS index 생성
dimension = len(embeddings[0])
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings).astype("float32"))

# 📌 9. 저장 (app.py 가 embeddings/ 에서 읽으므로 경로 통일)
os.makedirs("embeddings", exist_ok=True)
faiss.write_index(index, "embeddings/sermon_index.faiss")
np.save("embeddings/sermon_metadata.npy", np.array(metadata, dtype=object))

# 버전명 저장 (app.py에서 불러올 수 있도록)
version_info = {
    "embedding_version": version
}
with open("version_info.json", "w") as f:
    json.dump(version_info, f)

print(f"[OK] 버전 정보 저장 완료: version_{version}")
print(f"[OK] 전체 설교 {len(selected_files)}개 / 청크 {len(texts)}개 임베딩 완료")