-- =============================================================
-- 0001_sermon_chunks.sql
-- 설교 청크 + 임베딩 저장소 (pgvector) 및 유사도 검색 RPC
-- 임베딩 모델: OpenAI text-embedding-3-small (1536 차원)
-- =============================================================

-- 1. pgvector 확장 활성화
create extension if not exists vector;

-- 2. 설교 청크 테이블
create table if not exists public.sermon_chunks (
    id          bigint generated always as identity primary key,
    video_id    text,                       -- 출처 식별자(현재는 전사본 파일명 stem, 추후 YouTube video_id로 교체)
    sermon_date date,                        -- 설교 날짜 (파일명에서 추출)
    content     text        not null,        -- 설교 텍스트 청크
    embedding   vector(1536) not null,       -- text-embedding-3-small 임베딩
    created_at  timestamptz not null default now()
);

-- 3. 벡터 유사도 인덱스 (코사인 거리 기준)
--    설교 청크 수가 많지 않으면 IVFFlat 대신 정확 검색도 무방하나,
--    확장성을 위해 인덱스를 만들어 둔다. lists 는 데이터 규모에 맞춰 조정.
create index if not exists sermon_chunks_embedding_idx
    on public.sermon_chunks
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- video_id / 날짜로 조회·정렬할 일이 잦으므로 보조 인덱스
create index if not exists sermon_chunks_video_id_idx
    on public.sermon_chunks (video_id);
create index if not exists sermon_chunks_sermon_date_idx
    on public.sermon_chunks (sermon_date);

-- =============================================================
-- 4. 유사도 검색 RPC: match_sermons
--    사용자 질문 임베딩(query_embedding)과 코사인 유사도가 높은
--    설교 청크를 상위 match_count 개 반환한다.
--    - match_threshold: 0~1, 이 값 이상의 유사도만 반환 (기본 0)
--    - 유사도 similarity = 1 - 코사인거리
-- =============================================================
create or replace function public.match_sermons (
    query_embedding vector(1536),
    match_count     int   default 5,
    match_threshold float default 0.0
)
returns table (
    id          bigint,
    video_id    text,
    sermon_date date,
    content     text,
    similarity  float
)
language sql stable
as $$
    select
        sc.id,
        sc.video_id,
        sc.sermon_date,
        sc.content,
        1 - (sc.embedding <=> query_embedding) as similarity
    from public.sermon_chunks as sc
    where 1 - (sc.embedding <=> query_embedding) >= match_threshold
    order by sc.embedding <=> query_embedding   -- 코사인 거리 오름차순 = 유사도 내림차순
    limit match_count;
$$;
