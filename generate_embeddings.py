import os
import re
import sys
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 출력 깨짐/크래시 방지

# 📌 1. 환경변수 로드 (OpenAI + Supabase)
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Supabase: service_role 키 사용 (서버 사이드 insert, RLS 우회 목적)
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

# 📌 2. 설정
input_folder = "corrected_transcripts"        # LLM 교정본 사용
embedding_model = "text-embedding-3-small"     # 1536 차원
TABLE_NAME = "sermon_chunks"
CHUNK_SIZE = 1000                              # 청크 글자 수
EMBED_BATCH = 100                              # OpenAI 임베딩 1회 요청당 청크 수
INSERT_BATCH = 200                             # Supabase insert 1회당 행 수


# 📌 3. 임베딩 함수 (배치 처리)
def get_embeddings(batch_texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=embedding_model, input=batch_texts)
    return [item.embedding for item in response.data]


# 📌 4. 파일명에서 설교 날짜(YYYYMMDD) 추출 → ISO 문자열
def extract_date(filename: str) -> str | None:
    match = re.search(r"20\d{6}", filename)
    if match:
        return datetime.strptime(match.group(), "%Y%m%d").date().isoformat()
    return None


# 📌 5. 전체 설교 선택 (3년 필터 미적용 — B안 채택)
all_files = sorted(f for f in os.listdir(input_folder) if f.endswith(".txt"))
print(f"전체 설교 {len(all_files)}개 임베딩 시작 (필터 미적용)")

# 📌 6. 텍스트 로딩 + 1000자 청킹
#    각 청크에 출처(video_id = 파일명 stem)와 설교 날짜를 함께 보관한다.
chunks: list[dict] = []
for file in all_files:
    video_id = os.path.splitext(file)[0]
    sermon_date = extract_date(file)
    with open(os.path.join(input_folder, file), "r", encoding="utf-8") as f:
        content = f.read()
    for i in range(0, len(content), CHUNK_SIZE):
        chunks.append(
            {
                "video_id": video_id,
                "sermon_date": sermon_date,
                "content": content[i:i + CHUNK_SIZE],
            }
        )

print(f"총 {len(chunks)}개 청크 생성 — 임베딩 + Supabase 적재 시작")

# 📌 7. 임베딩 생성 후 Supabase 에 적재
rows: list[dict] = []
inserted = 0

for start in range(0, len(chunks), EMBED_BATCH):
    batch = chunks[start:start + EMBED_BATCH]
    embeddings = get_embeddings([c["content"] for c in batch])

    for chunk, embedding in zip(batch, embeddings):
        rows.append({**chunk, "embedding": embedding})

    print(f"[임베딩] {min(start + EMBED_BATCH, len(chunks))}/{len(chunks)}")

    # 버퍼가 INSERT_BATCH 이상 쌓이면 Supabase 에 적재
    while len(rows) >= INSERT_BATCH:
        supabase.table(TABLE_NAME).insert(rows[:INSERT_BATCH]).execute()
        inserted += INSERT_BATCH
        del rows[:INSERT_BATCH]
        print(f"[적재] {inserted}개 행 insert 완료")

# 남은 행 적재
if rows:
    supabase.table(TABLE_NAME).insert(rows).execute()
    inserted += len(rows)
    print(f"[적재] {inserted}개 행 insert 완료")

print(f"[OK] 설교 {len(all_files)}개 / 청크 {inserted}개 Supabase 적재 완료")
