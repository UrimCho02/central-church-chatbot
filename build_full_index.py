# -*- coding: utf-8 -*-
"""
3년 필터 미적용(B안) 비교용 인덱스 생성.
generate_embeddings.py 와 청킹 방식은 동일하게 두고, 날짜 필터만 제거해
clean_transcripts 의 모든 .txt 를 임베딩한다.
출력: embeddings/sermon_index_full.faiss, embeddings/sermon_metadata_full.npy
"""
import os
import sys
from openai import OpenAI
import faiss
import numpy as np
from dotenv import load_dotenv

# Windows 콘솔(cp949)에서 출력 깨짐/크래시 방지
sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

input_folder = "clean_transcripts"
embedding_model = "text-embedding-3-small"


def get_embedding(text):
    response = client.embeddings.create(model=embedding_model, input=text)
    return response.data[0].embedding


# 필터 없이 전체 .txt 선택
all_files = sorted(f for f in os.listdir(input_folder) if f.endswith(".txt"))
print(f"전체 설교 {len(all_files)}개 임베딩 시작 (필터 미적용)")

# generate_embeddings.py 와 동일한 1000자 청킹
texts = []
for file in all_files:
    with open(os.path.join(input_folder, file), "r", encoding="utf-8") as f:
        content = f.read()
    for i in range(0, len(content), 1000):
        texts.append((file, content[i:i + 1000]))

embeddings = []
metadata = []
for idx, (filename, chunk) in enumerate(texts):
    print(f"[{idx + 1}/{len(texts)}] {filename} 임베딩 중...")
    embeddings.append(get_embedding(chunk))
    metadata.append((filename, chunk))

dimension = len(embeddings[0])
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings).astype("float32"))

os.makedirs("embeddings", exist_ok=True)
faiss.write_index(index, "embeddings/sermon_index_full.faiss")
np.save("embeddings/sermon_metadata_full.npy", np.array(metadata, dtype=object))

print(f"[OK] 전체 인덱스 생성 완료: 설교 {len(all_files)}개 / 청크 {len(texts)}개")
