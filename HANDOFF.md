# 작업 핸드오프 — 2026-05-22 (퇴근 시점)

집에서 이어서 할 때 이 파일과 함께 Claude Code를 켜면 됩니다.

## 오늘 완료한 것 (christian-chatbot)

- OpenAI 크레딧 충전 → 재임베딩 정상화
- 3년 필터 A/B 비교 → **B안(필터 제거, 전체 설교) 채택**
- 전사본 STT 손상 발견("십일조"가 "11조"로 전사되는 등) → **LLM 교정 패스** 적용
  → `corrected_transcripts/` 262개 생성 (원본 `clean_transcripts/` 보존, 깨진 1개 제외)
- 교정본 재임베딩 → `embeddings/sermon_index.faiss` (262개 설교 / 4,348청크)
- `app.py`: 모델 `gpt-4` → `gpt-4o` (품질↑ 비용↓ 검증 완료)
- `app.py`: 상담 프롬프트 개선 (목회적 어조, "법적" 표현 차단, 설교 근거 강제)

→ `app.py`는 현재 교정된 전체 설교 + gpt-4o + 개선 프롬프트로 작동.

## 다음 작업 — 챗봇을 교회 홈페이지에 통합

**홈페이지:** https://central-church-website.vercel.app/ (React+Vite, Vercel 배포)
로컬 클론: `C:\Users\User\Desktop\Urim\central-church-website`

**방식:** React 채팅 컴포넌트 + 별도 파이썬 백엔드 API
- 프론트(React) → Vercel (이미 연결됨)
- 백엔드(파이썬 RAG) → Render 무료 티어 (이번에 새로 연결)
- ⚠️ OpenAI 키는 백엔드 환경변수로만. 프론트엔드 코드에 절대 넣지 않기.

**단계:**
1. ▶ **백엔드 API 작성** — `app.py` 로직을 FastAPI `/ask` 엔드포인트로 분리  ← 여기서 시작
2. 백엔드 Render 배포 (christian-chatbot을 GitHub에 올려야 함)
3. React 채팅 위젯을 `central-church-website/src/App.jsx`에 추가
4. 사이트 재배포 (GitHub push → Vercel 자동)

→ 다음 세션에서 "백엔드 API부터 시작하자"고 하면 1단계 진행.

## 미뤄둔 과제 (홈페이지 통합 후)

- 청킹 개선 — "주일 성수" 같이 설교 중간에만 언급되는 주제가 검색 안 됨
- 죽은 전사본 1개(`천국에서 큰 자`) 영상 재수집
- `version_info.json` 라벨 `262_00010101` cosmetic 수정
- 일회성 스크립트 정리: `build_full_index.py`, `compare_*.py`, `embeddings/sermon_index_full.*`

## 참고: 오늘 작업은 아직 git 커밋 안 됨
