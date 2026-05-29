# 작업 핸드오프 — 2026-05-29 (회사 PC 퇴근 시점)

## 진행 중: Next.js + Supabase(pgvector) 스택 마이그레이션
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
