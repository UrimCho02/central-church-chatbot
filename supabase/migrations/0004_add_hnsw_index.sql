-- =============================================================
-- 0004_add_hnsw_index.sql
-- HNSW 벡터 인덱스 추가 (만나 백필로 청크 4.8k → 16.7k 로 3.4배 증가)
-- =============================================================
-- 배경:
--   0002 에서 IVFFlat 인덱스를 제거하고 seq scan 으로 운영했다.
--   당시(약 4,348청크)엔 수십 ms 로 충분히 빨랐으나, 만나교회 백필
--   완료 후 총 16,722청크(1536차원)로 늘면서 seq scan 이 Supabase
--   기본 statement_timeout 을 넘겨 검색 요청이 실패한다 (57014).
--
-- 결정:
--   HNSW 인덱스 채택. 0002 에서 향후 방향으로 명시한 그대로다.
--     - IVFFlat: 사전 학습 필요 → 빈 테이블 문제 재발 여지
--     - HNSW: 사전 학습 불필요, recall 도 더 안정적
--   데이터가 이미 적재된 뒤 생성하므로 IVFFlat 처럼 클러스터 왜곡 없음.
--
-- 파라미터:
--   m=16, ef_construction=64 는 pgvector 기본값. 16k 규모에선
--   기본값으로 충분하다. 필요 시 ALTER INDEX 로 조정 가능.
--   런타임 recall/속도 조절은 SET hnsw.ef_search = <n> 으로.
-- =============================================================

create index if not exists sermon_chunks_embedding_idx
    on public.sermon_chunks
    using hnsw (embedding vector_cosine_ops);
