import argparse
import os
import pickle
import re
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
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
# 청킹: 문장(줄) 경계 기반 + overlap.
#   교정본은 '한 줄 = 한 문장' 구조라 줄을 묶어 청크를 만든다.
#   1000자 하드컷은 한 주제를 두 청크로 쪼개고 핵심 대목을 묻어 검색 실패를
#   유발했음(헌금/구원/기도 질문이 전용 설교를 못 끌어옴) → 작게+겹치게로 전환.
CHUNK_TARGET = 500                             # 청크 목표 글자 수(문장 경계로 ±)
CHUNK_OVERLAP = 120                            # 청크 간 겹침 글자 수
EMBED_BATCH = 100                              # OpenAI 임베딩 1회 요청당 청크 수
INSERT_BATCH = 200                             # Supabase insert 1회당 행 수
DELETE_BATCH = 500                             # 삭제 배치 크기(전체 삭제 시 timeout 회피)
CACHE_FILE = "_embeddings_cache.pkl"           # 임베딩 캐시(적재 실패 시 재임베딩 생략)


# 📌 3. 임베딩 함수 (배치 처리 + rate limit 백오프)
def get_embeddings(batch_texts: list[str], max_retries: int = 6) -> list[list[float]]:
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=embedding_model, input=batch_texts
            )
            return [item.embedding for item in response.data]
        except RateLimitError:
            wait = 2 ** attempt  # 1,2,4,8,16,32초
            print(f"    rate limit(TPM) — {wait}s 대기 후 재시도 ({attempt + 1}/{max_retries})")
            time.sleep(wait)
    raise RuntimeError("임베딩 rate limit 재시도 초과")


# 📌 4. 파일명에서 설교 날짜(YYYYMMDD) 추출 → ISO 문자열
def extract_date(filename: str) -> str | None:
    match = re.search(r"20\d{6}", filename)
    if match:
        return datetime.strptime(match.group(), "%Y%m%d").date().isoformat()
    return None


# 📌 4-1. 문장 경계 + overlap 청킹
_SENT_SPLIT = re.compile(r"(?<=[.?!])\s+")


def split_sentences(text: str, max_len: int = CHUNK_TARGET) -> list[str]:
    """교정본은 대체로 한 줄=한 문장. 다만 문장부호 없이 길게 이어진 줄이
    섞여 있어(거대 청크 유발), max_len 초과 줄은 문장부호로, 그래도 길면
    글자 단위로 더 쪼개 모든 단위를 max_len 이하로 만든다."""
    units: list[str] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if len(ln) <= max_len:
            units.append(ln)
            continue
        for s in _SENT_SPLIT.split(ln):
            s = s.strip()
            if not s:
                continue
            if len(s) <= max_len:
                units.append(s)
            else:  # 문장부호도 없는 장문 → 하드 분할
                units.extend(s[i:i + max_len] for i in range(0, len(s), max_len))
    return units


def chunk_text(
    text: str, target: int = CHUNK_TARGET, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """문장을 target 글자까지 묶어 청크 생성. 청크 끝 문장 일부(~overlap자)를
    다음 청크에 다시 포함해 경계에서 의미가 끊기지 않게 한다."""
    sents = split_sentences(text)
    n = len(sents)
    chunks: list[str] = []
    i = 0
    while i < n:
        cur_len = 0
        j = i
        # 최소 한 문장은 담되, target 을 넘기지 않는 선까지 문장을 채운다
        while j < n and (cur_len == 0 or cur_len + 1 + len(sents[j]) <= target):
            cur_len += len(sents[j]) + 1
            j += 1
        chunks.append(" ".join(sents[i:j]))
        if j >= n:
            break
        # overlap: 끝에서부터 ~overlap 자만큼 문장을 되짚어 다음 시작점으로
        back = 0
        k = j
        while k > i + 1 and back < overlap:
            k -= 1
            back += len(sents[k]) + 1
        i = k  # k >= i+1 보장 → 항상 전진
    return chunks


# 📌 5. 전체 설교 → 청크 목록 생성
#    각 청크에 출처(video_id = 파일명 stem)와 설교 날짜를 함께 보관한다.
#    skip_video_ids 가 주어지면 그 set 에 속한 설교는 건너뛴다(증분 모드).
def build_chunks(skip_video_ids: set[str] | None = None) -> list[dict]:
    all_files = sorted(f for f in os.listdir(input_folder) if f.endswith(".txt"))
    skip = skip_video_ids or set()
    target_files = [f for f in all_files if os.path.splitext(f)[0] not in skip]
    skipped = len(all_files) - len(target_files)
    print(
        f"설교 파일 {len(all_files)}개 (이미 적재 {skipped} / 처리 대상 {len(target_files)}) — "
        f"문장경계 청킹(target {CHUNK_TARGET}자, overlap {CHUNK_OVERLAP}자)"
    )
    chunks: list[dict] = []
    for file in target_files:
        video_id = os.path.splitext(file)[0]
        sermon_date = extract_date(file)
        with open(os.path.join(input_folder, file), "r", encoding="utf-8") as f:
            content = f.read()
        for piece in chunk_text(content):
            if len(piece) < 15:  # overlap 잔여물/짧은 끝문장 등 노이즈 청크 제외
                continue
            chunks.append(
                {"video_id": video_id, "sermon_date": sermon_date, "content": piece}
            )
    return chunks


# 📌 5-1. Supabase 에 이미 적재된 video_id 목록 (증분 모드용)
#    page 단위로 가져와 distinct set 로 모은다(supabase-py 가 DISTINCT 직접 미지원).
def fetch_existing_video_ids() -> set[str]:
    seen: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        rows = (
            supabase.table(TABLE_NAME)
            .select("video_id")
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not rows:
            break
        seen.update(r["video_id"] for r in rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return seen


# 📌 6. 임베딩 (전부 메모리에 모은 뒤 적재 → 실패 시 기존 데이터 보존)
def embed_all(chunks: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for start in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[start:start + EMBED_BATCH]
        embeddings = get_embeddings([c["content"] for c in batch])
        for chunk, embedding in zip(batch, embeddings):
            rows.append({**chunk, "embedding": embedding})
        print(f"[임베딩] {min(start + EMBED_BATCH, len(chunks))}/{len(chunks)}")
        time.sleep(1.2)  # TPM(분당 100만 토큰) 한도 아래로 페이싱
    return rows


# 📌 7. 기존 행을 배치로 삭제
#    전체를 한 번에 delete 하면 삭제된 행(대용량 벡터)을 통째로 반환하다
#    statement timeout 이 남 → id 배치로 나눠 삭제한다.
def clear_table() -> int:
    deleted = 0
    while True:
        ids = supabase.table(TABLE_NAME).select("id").limit(DELETE_BATCH).execute().data
        if not ids:
            break
        supabase.table(TABLE_NAME).delete().in_("id", [r["id"] for r in ids]).execute()
        deleted += len(ids)
        print(f"[삭제] {deleted}개 제거...")
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="설교 텍스트 → Supabase 임베딩 적재. 기본은 증분(새 설교만), "
        "--rebuild 시 기존 데이터 전체 삭제 후 재적재."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="기존 sermon_chunks 전체 삭제 후 재임베딩/재적재 (청킹·임베딩 모델 교체 시).",
    )
    args = parser.parse_args()

    if args.rebuild:
        skip_ids: set[str] = set()
        print("[모드] 전체 재적재 (--rebuild)")
    else:
        skip_ids = fetch_existing_video_ids()
        print(f"[모드] 증분 — Supabase 에 이미 있는 video_id {len(skip_ids)}건 건너뜀")

    # 임베딩은 비싸므로 캐시 → 적재 실패 후 재실행 시 재임베딩 생략
    if os.path.exists(CACHE_FILE):
        print(f"[캐시] {CACHE_FILE} 에서 임베딩 로드 (재임베딩 생략)")
        with open(CACHE_FILE, "rb") as fh:
            rows = pickle.load(fh)
    else:
        chunks = build_chunks(skip_video_ids=skip_ids)
        if not chunks:
            print("[OK] 새로 적재할 설교 없음 — 종료")
            return
        print(f"총 {len(chunks)}개 청크 생성 — 임베딩 시작")
        rows = embed_all(chunks)
        with open(CACHE_FILE, "wb") as fh:
            pickle.dump(rows, fh)
        print(f"[OK] 임베딩 {len(rows)}개 완료 → 캐시 저장")

    # 전체 재적재 모드에서만 기존 행 삭제. 증분 모드는 append-only.
    if args.rebuild:
        print("[삭제] 기존 행 제거 시작...")
        clear_table()

    inserted = 0
    for start in range(0, len(rows), INSERT_BATCH):
        supabase.table(TABLE_NAME).insert(rows[start:start + INSERT_BATCH]).execute()
        inserted += len(rows[start:start + INSERT_BATCH])
        print(f"[적재] {inserted}/{len(rows)}개 행 insert 완료")

    print(f"[OK] 청크 {inserted}개 Supabase 적재 완료")
    os.remove(CACHE_FILE)  # 성공 시 캐시 정리
    print(f"[정리] {CACHE_FILE} 삭제 완료")


if __name__ == "__main__":
    main()
