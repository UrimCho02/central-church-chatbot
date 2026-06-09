# 작업 핸드오프 — 2026-06-09 (iOS 자동확대 + 프롬프트 톤 수정) ⭐ 최신

## 한 줄 요약
모바일 위젯 마지막 버그(아이폰 자동확대) 수정 + 교회 찾는 질문에 대한 답변 톤 개선. 둘 다 실기/로컬 검증 완료. 프롬프트는 **`rag.py`·`api/ask.ts` 양쪽 동일하게** 수정.

## 1. iOS 입력창 자동확대 (`b00c108`, central-church-website)
- 원인: 아이폰 Safari는 16px 미만 입력창 포커스 시 화면을 자동확대(auto-zoom) → 패널이 "커지며" 하단 전송버튼이 보이는 영역 밖으로 밀림. (06-07 `6ae245c`는 키보드 높이만 보정했고 이 zoom은 못 잡았음)
- 조치: `src/App.jsx` textarea 글씨 14px → **16px**(자동확대 차단) + `index.html` viewport 메타에 `interactive-widget=resizes-content`(Android 키보드 대응). 기존 `visualViewport` 높이 보정은 iOS 폴백으로 유지. **아이폰 실기 검증 완료(안 밀림).**

## 2. 프롬프트 톤 — 교회 찾는 질문 대응 (`d8770ba` chatbot / `0a280f8` website)
- 증상: "어떤 교회를 찾아야 하나" 류 질문에도 기계적으로 "담임 목사님과 상담" 맺음말이 붙어 교회를 찾는 사람에게 어색.
- 조치(`generate_prompt`): ① 안내를 질문자 상황별 분기 — 기존 신자→담임 목사님 상담, 교회 탐색 중→**센트럴처치 설교 청취+예배 방문 권유**, 매 답변 기계적 첨부 금지. ② 프롬프트/시스템 메시지에 **"센트럴처치" 정체성 명시**([설교 내용]=센트럴처치 설교)해 방문 추천이 자연스럽게 나오도록.
- 로컬 검증: 교회 탐색 질문→센트럴처치 방문 초대 / 기도 고민(기존 신자)→담임 목사님 상담 맺음(회귀 없음).
- ⚠️ 톤·길이 등 추가 수정 시 **두 파일 프롬프트를 항상 동일하게** 유지할 것.

## ▶️ 다음 (아래 06-07 섹션 계획 그대로)
- 목사님 검수 → 피드백 반영 → `chat-widget-wip` main 머지(라이브) → Render 삭제.

---

# 작업 핸드오프 — 2026-06-07

## 한 줄 요약
검색 품질(청킹) 대폭 개선 + 질문/답변 누적 로깅(양쪽 백엔드) + 모바일 전송버튼 오터치 수정 완료.
**목사님 검수 준비 끝.** 남은 건 검수 → 피드백 반영 → `chat-widget-wip` main 머지(라이브) → Render 삭제.

## 두 레포 현재 상태 (모두 push 완료)
| 레포 | 브랜치 | 최신 커밋 | 상태 |
|---|---|---|---|
| central-church-chatbot (백엔드) | `main` | `d5de6ac` | 청킹 재설계 + chat_logs 로깅. Render 라이브. |
| central-church-website (프론트) | `chat-widget-wip` | `6ae245c` | Vercel `api/ask.ts` 로깅 + 모바일 UX 수정(전송버튼·키보드). **main 미머지.** |

## 오늘(2026-06-06~07) 한 일

### 1. 검색 품질 — 청킹 재설계 (핵심)
- **증상:** "헌금/구원/기도" 같은 주제형 질문이 목사님의 해당 주제 전용 설교를 못 끌어오고 일반론으로 답함.
- **진단**(`debug_rag.py`로 매칭 청크+유사도 측정): 전사 오류(십일조→"11조")는 `corrected_transcripts/` 교정본으로 이미 해결됐으나, **1000자 하드컷 청킹**이 핵심 대목을 잘라/묻어 전용 설교가 top_k 밖으로 밀림. (예: 헌금 질문에 「온전한 십일조」가 6위 → top_k=5에 잘림)
- **조치:** `generate_embeddings.py`를 **문장경계 청킹(target 500자 + overlap 120자)**로 재설계, Supabase 재적재(4,348 → **12,562청크**). 재적재 안전장치: 임베딩 디스크 캐시(`_embeddings_cache.pkl`, gitignore) + 배치 삭제(전체 delete 시 statement timeout 회피) + TPM 백오프.
- **결과**(`chunking_eval_20260606.md`): 헌금→「온전한 십일조」 6위→1위, 구원→「피를 볼 때에」(유월절) 1위 등 전 질문 유사도 상승. Supabase 공유라 Render·Vercel 즉시 반영.

### 2. 질문/답변 누적 로깅 (chat_logs)
- `0003_chat_logs.sql`: `chat_logs` 테이블 + RLS(서버 전용, 공개 접근 차단). **Supabase SQL Editor에서 실행 완료(검증함).**
- 백엔드: `rag.py` `log_qa()`(best-effort) + `api.py` `/ask`에서 호출.
- 프론트: Vercel `api/ask.ts` 응답 후 best-effort insert(실 홈페이지 경로). **양쪽 검증 완료.**
- 조회: Supabase 대시보드 **Table Editor → chat_logs** (RLS로 공개 API엔 안 보임 = 프라이버시).

### 3. 모바일 UX 수정 (`src/App.jsx`) — 2건
- **전송버튼 오터치**(`1e19067`): 입력창-버튼 간격 `gap-2`→`gap-3`, 모바일(`pointer: coarse`)에선 Enter=줄바꿈(전송은 버튼만). 데스크탑 Enter=전송 유지.
- **키보드로 입력창/버튼이 화면 밖으로 밀림**(`6ae245c`): 패널 `fixed inset-0`→`top-0 h-[100dvh]` + `visualViewport`에 맞춰 높이·위치 보정(키보드만큼 패널이 줄어듦). 데스크탑 400×640 그대로.
- ⚠️ 둘 다 터치/키보드 동작이라 코드 검증 불가 — **휴대폰(특히 iOS)에서 직접 재확인 필요.**

## ▶️ 다음 작업 (순서)
1. **모바일 휴대폰 재확인** (오터치로 조기 전송 안 되는지 + 키보드 올라올 때 입력창/전송버튼이 화면에 보이는지, 특히 iOS)
2. **목사님 검수** — 프리뷰 URL(보호 꺼둠, 로그인 불필요):
   `https://central-church-website-git-chat-widget-wip-urimcho02s-projects.vercel.app`
   - off-topic(비트코인류)에 신앙관점으로 답하는 경향 → 목사님 의견 받기(거절형 원하면 `match_threshold` 추가)
   - 검수 중 질문은 chat_logs에 자동 누적됨
3. 피드백 반영 (톤/길이는 `rag.py` generate_prompt + `api/ask.ts` 프롬프트 **양쪽 동일하게** 수정)
4. **공개 런칭 전**: 위젯 disclaimer에 "질문이 저장될 수 있습니다" 한 줄
5. `chat-widget-wip` → main 머지 + push = centralchurch.kr 라이브 (Vercel env 3개 Production 스코프 확인) → Render 삭제

## 추가 개선 여지 (검수 후)
- off-topic 거절형(`match_threshold`) — 단 주제형도 유사도 0.33~0.54라 보정 주의(정상 주제까지 막힐 위험)
- 청크별 요약/HyDE 임베딩으로 주제 매칭 강화, top_k 튜닝
- `debug_rag.py "질문" [N]` 으로 변경 후 회귀 측정

## ⚙️ 다른 PC에서 이어가려면
- ⚠️ **시작 시 두 레포 다 `git fetch` 먼저** — 회사/집 PC가 자주 앞서감(이번 세션에도 양쪽 다 behind였음).
  - central-church-chatbot: `git pull` (main)
  - central-church-website: `git fetch && git checkout chat-widget-wip && git pull`
- `.env`는 PC마다 직접 생성(git 추적 X): chatbot = `OPENAI_API_KEY`+`SUPABASE_URL`+`SUPABASE_SERVICE_ROLE_KEY` / website = 위 3개+`VITE_YOUTUBE_API_KEY`
- 의존성: chatbot `pip install -r requirements.txt`(supabase 포함), website `npm install`
- 클라우드(Supabase 데이터·로그, Render, Vercel)는 공유라 PC 무관.

---

# 작업 핸드오프 — 2026-06-05 (퇴근 시점)

## 한 줄 요약
백엔드를 **Render(Python) → Vercel 서버리스 함수(TypeScript)** 로 옮기는 작업까지 끝냈고,
**프리뷰에서 검증 완료**. 남은 건 **목사님 검수 → main 머지(라이브) → Render 삭제** 뿐.

## 두 레포 현재 상태 (모두 push 완료 — 어느 PC서든 pull 가능)
| 레포 | 브랜치 | 최신 커밋 | 상태 |
|---|---|---|---|
| `christian-chatbot` (백엔드) | `main` | `eb62918` | Supabase RPC + polish 제거 + repo 정리. Render에 라이브. |
| `central-church-website` (프론트) | `chat-widget-wip` | `ddc05fd` | 위젯 + `api/ask.ts`(Vercel 함수). 프리뷰 검증됨. **main 미머지.** |

## 오늘(2026-06-05) 한 일 — 시간순
1. **christian-chatbot 마이그레이션 2단계 B** (main): `rag.py` FAISS→`match_sermons` RPC, supabase 런타임 승격/faiss-cpu 제거.
2. **데이터 적재**: 집에선 스키마만 만들어졌고 테이블이 비어 있었음 → `generate_embeddings.py` 실행 → **262설교/4,348청크** 적재.
3. **IVFFlat 버그 수정** (`0002` 마이그레이션, SQL Editor에서 실행): 빈 테이블에 만든 인덱스가 recall 깨뜨림 → 인덱스 drop. (교훈: 인덱스는 데이터 적재 후 생성)
4. **라이브 전환**: main 머지+push → Render에 SUPABASE env 등록 → 배포 검증.
5. **repo 정리**: 런타임 미사용 FAISS 파일 + 일회성 compare 스크립트 제거.
6. **비용·속도 최적화**: A/B 비교 후 polish 단계 제거 (응답당 GPT-4o 2→1, 비용·시간 ~절반).
7. **Render 탈출 — Vercel 서버리스 함수** (central-church-website `chat-widget-wip`):
   - `api/ask.ts`: rag.py 로직 TS 포팅(임베딩→Supabase `match_sermons` RPC→GPT-4o, 프롬프트 동일, maxDuration 30s, 클라이언트 지연생성+env 검증).
   - 위젯: Render URL → 동일 출처 `/api/ask` (CORS 제거). 콜드스타트 문구 변경.
   - deps: openai, @supabase/supabase-js (+dev @vercel/node).
   - **프리뷰 검증 완료**: `/api/ask` HTTP 200 + 브라우저 위젯 정상.

## ▶️ 다음에 이어서 할 일 (순서)
1. **목사님 검수** — 프리뷰 URL 전달 (보호 꺼둬서 로그인 불필요):
   `https://central-church-website-git-chat-widget-wip-urimcho02s-projects.vercel.app`
2. 피드백 반영 (필요시 톤·길이 — `christian-chatbot/rag.py` generate_prompt 또는 `central-church-website/api/ask.ts` 동일 프롬프트 **양쪽 다** 수정해야 일관).
3. **`chat-widget-wip` → main 머지 + push** = centralchurch.kr 본 사이트에 챗봇 라이브.
   - ⚠️ 머지 전 Vercel env 3개가 **Production 스코프**에도 있는지 확인 (없으면 위젯은 뜨지만 /api/ask 500).
4. **Render 서비스 삭제** — 머지 후 아무도 안 씀 (위젯은 /api/ask 사용, 남은 건 옛 `/demo`뿐). 콜드스타트 완전 작별.
5. **정리**: `chat-widget-wip`의 trigger-rebuild 빈 커밋들 정돈, Render `/demo` 잔재.

## ⚙️ 다른 PC에서 이어가려면 (중요 — `.env`는 git 추적 안 됨)
1. 두 레포 최신화:
   - `christian-chatbot`: `git pull` (main)
   - `central-church-website`: `git fetch && git checkout chat-widget-wip && git pull`
2. **`.env` 파일을 PC마다 직접 생성** (git에 없음). 필요한 키:
   - `christian-chatbot/.env`: `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - `central-church-website/.env`: 위 3개 + `VITE_YOUTUBE_API_KEY` (`.env.example` 참고)
3. 의존성: `christian-chatbot`은 `pip install -r requirements.txt`, `central-church-website`는 `npm install`.
4. 클라우드(Supabase 데이터, Render, Vercel)는 공유 상태라 PC 무관.

## 현재 안전 상태
- **본 사이트(centralchurch.kr)**: 챗봇 아직 안 뜸 (main 미머지) ✅
- **Render 백엔드**: 살아있음 (삭제 금지 — 머지·검증 후). 현재 유일 용도 = 옛 `/demo`.
- **Vercel 프리뷰 보호**: 꺼둠 (검수용). 검수 후 다시 켜도 됨.

---

# 작업 핸드오프 — 2026-06-05 (회사 PC, 오전) — 기록 보존
2단계 B 상세는 위 최신 섹션에 통합됨. (이전 메모: `rag-supabase-rpc` 브랜치 작업 → 이후 main 머지 `aec0481`.)

---

# 작업 핸드오프 — 2026-05-29 (회사 PC 퇴근 시점)

## 진행 중: Next.js + Supabase(pgvector) 스택 마이그레이션 (2단계 A)
Python+FAISS+Streamlit → Next.js+Supabase 로 이전 중. **DB + 데이터 입력 파이프라인부터** 손대는 단계.

### 오늘 완료
1. **Supabase SQL 마이그레이션** — `supabase/migrations/0001_sermon_chunks.sql`
   - pgvector 확장, `sermon_chunks` 테이블(id, video_id, sermon_date, content, `embedding vector(1536)`, created_at)
   - 코사인 IVFFlat 인덱스 + `match_sermons(query_embedding, match_count, match_threshold)` RPC
   - ⚠️ **아직 Supabase에 적용 안 됨** — 집에서 Supabase 프로젝트 SQL Editor에 이 파일 실행부터 해야 함.
2. **`generate_embeddings.py`** — FAISS/numpy 제거, `supabase-py`로 `sermon_chunks`에 insert로 리팩토링.
   - 임베딩 100개씩 배치, Supabase 200행씩 배치 insert. 모델 `text-embedding-3-small`(1536).
   - `video_id`=전사본 파일명 stem(실제 YouTube id 매핑 없어 임시), `sermon_date`=파일명 `20\d{6}` 추출.
3. **자막 파이프라인 채택** — Whisper STT → YouTube 자동자막 fetch 로 교체.
   - A/B 검증(십일조 설교, raw ASR 비교): 자막이 Whisper보다 **어휘 정확도 우위**(Whisper `만군의 여호와→방군의 여우와` 깨짐, 자막은 정확). 단 `십일조→11조`는 둘 다 틀림 → **`correct_transcripts.py` LLM 교정 패스는 계속 필요**. 이득은 영상당 수 분→1초 미만 + 오디오 다운로드/Whisper 제거.
   - `update_transcribe_and_clean.py` 전면 교체: `list_unprocessed_videos`→`fetch_subtitle`(yt-dlp `--write-auto-subs --sub-langs ko --skip-download`)→`vtt_to_text`→`clean`→`clean_transcripts/`.
   - `vtt_to_text.py` 신규(타임스탬프·태그·롤링중복 제거, cue별 줄 유지 → `batches()` 5개 ~3000자 분할 검증 완료).
   - 적용한 교훈: `:`→`_` 파일명 정규화(중복 수집 방지), `youtube:lang=ko`+`Accept-Language`(제목 영어 번역 방지), 자식 프로세스 `PYTHONUTF8=1`(cp949 깨짐 방지).
4. `requirements-pipeline.txt`에 `supabase==2.11.0` 추가. `.gitignore`에 `subs_tmp/`, `channel_list.txt`.

### 다음 작업 (집에서)
- **B. `rag.py` FAISS → `match_sermons` RPC 전환** (예정, 미착수)
  - 시작 시 `faiss.read_index`/`np.load` 제거 → 질문 임베딩 후 `supabase.rpc("match_sermons", {query_embedding, match_count})` → 반환 `content` 리스트를 컨텍스트로. `api.py`는 그대로.
- B 끝난 뒤 **의존성 정리 한 번에**: `openai-whisper`(미사용), `faiss-cpu`(rag.py가 아직 사용 중이라 B 전엔 제거 금지) 제거.
- 이후 Next.js 프론트 마이그레이션.

### 환경 추가 (중요)
- 새 `.env` 변수 필요: **`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`** (service_role은 서버 전용, 클라이언트 노출 금지). 집 PC `.env`에 추가.
- 순서: ① Supabase에 0001 SQL 실행 → ② `.env`에 Supabase 키 → ③ `pip install -r requirements-pipeline.txt`(supabase) → ④ `generate_embeddings.py` 실행.

---

# 작업 핸드오프 — 2026-05-25 (집 PC 퇴근 시점)

## 오늘 완료한 것

### central-church-chatbot (백엔드)
- `rag.py` — 검색/프롬프트/GPT 호출/`polish_text` 로직 분리 (`app.py`에서 추출)
- `api.py` — FastAPI `/ask` + `/health`, Vercel + localhost:5173 CORS
- `requirements.txt` 런타임용 정리, `requirements-pipeline.txt`로 whisper/yt-dlp 분리
- `.gitignore`에서 무력화돼 있던 `embeddings/` 제외 룰 제거 (FAISS 인덱스 26MB+10MB 이미 추적 중이었음)
- GitHub push 완료 (`95dbdeb`, `dff3675`)
- **Render 배포 완료** — https://central-church-chatbot.onrender.com
  - Build: `pip install -r requirements.txt`
  - Start: `uvicorn api:app --host 0.0.0.0 --port $PORT`
  - Free 티어 (15분 idle 후 sleep, 콜드 스타트 ~30-60초)
- 라이브 검증: `/health` 200, `/ask` 200 (~5-10초 응답), CORS preflight OK

### central-church-website (프론트)
- 집 PC에 clone 완료 (`C:\Users\hebe0\central-church-website`)
- `npm install` 완료
- `src/App.jsx`에 **ChatWidget 컴포넌트 추가** → **`chat-widget-wip` 브랜치로 push** (main 머지 금지)
  - 우하단 FAB → 클릭 시 패널 오픈 (모바일 풀스크린 / 데스크탑 400×640)
  - `slate-800` 헤더 + indigo 톤 disclaimer + 메시지 버블 (user indigo / assistant gray / error red)
  - 8초 콜드 스타트 힌트, 90초 AbortController 타임아웃
  - lucide-react 아이콘: `MessageCircle`, `Send`
- `npm run dev`에서 동작 확인 (Vite 5173, 실제 Render 호출 정상 응답 받음)
- ⚠️ Vercel이 브랜치별 프리뷰 자동 배포한다면 `chat-widget-wip` 도 프리뷰 URL이 생길 수 있음. 그건 production(main) 영향 없고 — 어차피 목사님 검수는 백엔드 `/demo` 페이지로 따로 갈 거라 무시.

**다른 PC에서 위젯 코드 보려면:**
```bash
cd central-church-website
git fetch origin
git checkout chat-widget-wip
```

## 다음 작업 — 챗봇 목사님 검수용 별도 배포

본 사이트(`central-church-website.vercel.app`)에 붙이기 전에 챗봇만 격리해서
담임 목사님께 톤/품질 검수 요청하기 위함. main 브랜치에 push 금지.

### 추천: 백엔드에 `/demo` HTML 페이지 추가 (옵션 A)
- `api.py`에 `GET /demo`를 vanilla HTML+JS 채팅 UI로 응답
  (또는 `static/demo.html`을 `StaticFiles`로 마운트)
- 기존 ChatWidget JSX 로직을 한 번만 vanilla로 포팅 (디자인 단순 버전으로 충분)
- Render에 push만 하면 자동 재배포 → 공유 URL:
  `https://central-church-chatbot.onrender.com/demo`
- 장점: "챗봇만" 깔끔, 새 인프라 X, 콜드 스타트 안내까지 같이 가능

### 대안
- **B. Vercel 프리뷰 브랜치** (5분): `central-church-website` 레포에 `chat-preview` 브랜치 push → Vercel 자동 프리뷰 URL. 목사님이 풀 사이트 + 챗봇을 같이 보게 됨.
- **C. 별도 Vite 앱** (30분+): 새 레포/프로젝트로 분리. 가장 격리되지만 설정 부담.

### 목사님 검수 후
1. 피드백 반영 (프롬프트 톤 조정, 답변 길이, disclaimer 문구 등)
2. `central-church-website/src/App.jsx`의 ChatWidget commit + push → Vercel 자동 배포로 본 사이트에 노출
3. demo 페이지 제거 (선택)

## 미뤄둔 과제 (목사님 검수 후)

- 청킹 개선 — "주일 성수" 같이 설교 중간에만 언급되는 주제가 검색 안 됨
- 죽은 전사본 1개(`천국에서 큰 자`) 영상 재수집
- `version_info.json` 라벨 `262_00010101` cosmetic 수정
- 일회성 스크립트 정리: `build_full_index.py`, `compare_*.py`, `embeddings/sermon_index_full.*`
- `requirements.txt` 보안 취약점 점검 (`central-church-website` npm install 시 49 vulnerabilities 보고됨 — 사용 중 패키지인지 확인 필요)

## 환경 노트

- 집 PC: `C:\Users\hebe0\central-church-chatbot`, `C:\Users\hebe0\central-church-website`
- 회사 PC: `C:\Users\User\Desktop\Urim\central-church-chatbot`, `C:\Users\User\Desktop\Urim\central-church-website`
- `.env` (OPENAI_API_KEY)는 PC마다 직접 만들어야 함 — git 추적 X
- Render는 같은 키를 환경변수로 들고 있음
