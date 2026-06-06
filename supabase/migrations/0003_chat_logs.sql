-- =============================================================
-- 0003_chat_logs.sql
-- 사용자 질문/답변 누적 로그.
--   홈페이지 챗봇 실사용 기록을 쌓아 목사님 열람·품질 개선에 활용.
--   Render(Python)·Vercel(TS) 어느 백엔드로 들어와도 같은 테이블에 누적된다.
-- ⚠️ Supabase SQL Editor에서 직접 실행해야 적용됨 (0001/0002와 동일).
-- =============================================================

create table if not exists public.chat_logs (
    id          bigint generated always as identity primary key,
    question    text        not null,
    answer      text        not null,
    created_at  timestamptz not null default now()
);

-- 최근 로그 조회·정렬용
create index if not exists chat_logs_created_at_idx
    on public.chat_logs (created_at desc);

-- =============================================================
-- 프라이버시: 상담 내용은 개인정보. RLS 켜서 익명/클라이언트 접근 전면 차단.
--   정책을 만들지 않으므로 anon·authenticated 는 read/write 불가.
--   서버(service_role 키)는 RLS 를 우회하므로 insert/select 가능.
--   → 클라이언트에 service_role 키를 노출하지 말 것(서버 전용).
-- =============================================================
alter table public.chat_logs enable row level security;
