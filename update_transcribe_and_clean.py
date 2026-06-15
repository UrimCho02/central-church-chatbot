# -*- coding: utf-8 -*-
"""
YouTube 자막 기반 설교 전사 수집 (구 Whisper STT 파이프라인 대체).

[변경 이유 / 검증]  memory: youtube-subs-vs-whisper
  기존: 영상 오디오(m4a) 다운로드 → Whisper medium STT (영상당 수 분).
  변경: YouTube 한국어 자동자막(ko)을 바로 fetch (영상당 1초 미만).
  A/B 결과 자막 품질이 Whisper 동급 이상이며, 오디오 다운로드/Whisper 단계를
  통째로 제거할 수 있어 채택.

[흐름]
  1. 채널 영상 목록(제목+id) 추출 → 이미 처리된 설교는 제외
  2. 각 영상의 ko 자동자막 VTT fetch → vtt_to_text 정제 → 경량 clean
     → clean_transcripts/<제목>.txt
  3. (다운스트림, 별도 실행)
       python correct_transcripts.py     # ASR 오류 LLM 교정
       python generate_embeddings.py      # 임베딩 → Supabase

[주의]
  - 자막은 ASR이라 신앙 어휘 오류(십일조→11조 등)가 남는다.
    따라서 correct_transcripts.py 교정 패스는 그대로 필요하다.
  - Windows에서 yt-dlp 출력이 cp949로 깨지지 않도록 자식 프로세스에
    PYTHONUTF8/PYTHONIOENCODING 을 강제한다.
  - 채널 listing 제목 영어 자동번역 방지 옵션 적용(memory: ytdlp-korean-titles).
"""
import os
import re
import subprocess
import sys

from vtt_to_text import vtt_to_text

sys.stdout.reconfigure(encoding="utf-8")

# =========================
# 경로 / 설정
# =========================
channel_url = "https://www.youtube.com/@centralchurch5467/videos"
clean_folder = "clean_transcripts"
sub_tmp_folder = "subs_tmp"

os.makedirs(clean_folder, exist_ok=True)
os.makedirs(sub_tmp_folder, exist_ok=True)

# yt-dlp 자식 프로세스가 UTF-8로 출력하도록 강제 (Windows cp949 깨짐 방지)
_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

# 채널 listing 시 제목이 영어로 자동번역되는 문제 방지 (memory: ytdlp-korean-titles)
_LANG_ARGS = [
    "--extractor-args", "youtube:lang=ko",
    "--add-header", "Accept-Language:ko-KR,ko;q=0.9",
]

# YT_COOKIES 환경변수가 잡혀 있으면 yt-dlp 에 쿠키 파일 경로를 전달한다.
# CI(Azure 데이터센터 IP)는 YouTube 봇 체크("로그인하여 봇이 아님을 확인하세요")
# 를 받기 때문에 로그인된 세션 쿠키가 필요. 로컬에선 미설정이라 동작 변화 없음.
_COOKIE_ARGS = (
    ["--cookies", os.environ["YT_COOKIES"]] if os.environ.get("YT_COOKIES") else []
)

# YouTube 의 n-sig 챌린지를 풀려면 JS 런타임(deno) + 챌린지 solver 스크립트가
# 모두 필요. solver 스크립트는 yt-dlp 가 기본적으로 다운로드를 막아두므로
# 명시적으로 opt-in: --remote-components ejs:github (yt-dlp 권장 옵션).
# 미적용 시 "Requested format is not available" 로 자막 fetch 가 실패.
_EJS_ARGS = ["--remote-components", "ejs:github"]

# 자막 텍스트에서 제거할 추임새/군더더기 (구 clean_text 와 동일)
_FILLER = re.compile(r"(할렐루야|아멘|맞죠|그러니까요|뭐예요|그렇죠|여러분)")


def normalize_name(name):
    return os.path.splitext(name)[0].strip()


def sanitize_title(title):
    """YouTube 제목 → 파일명 stem.
    기존 clean_transcripts 파일명 규칙(':' → '_')과 일치시켜 중복 수집을 막는다."""
    title = title.replace(":", "_")
    title = re.sub(r'[\\/*?"<>|]', "_", title)  # Windows 파일명 금지문자
    return title.strip()


def clean(text):
    """자막 텍스트 경량 정제. 줄 구조는 유지한다.
    (correct_transcripts.py 가 줄 단위로 ~3000자 배치를 나누므로 줄바꿈이 필요)"""
    lines = []
    for line in text.splitlines():
        line = _FILLER.sub("", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


# =========================
# 1. 미처리 영상 목록 추출
# =========================
def list_unprocessed_videos():
    """채널 영상 중 아직 clean_transcripts 에 없는 (stem, video_id) 목록."""
    print("🌐 유튜브 영상 목록 확인 중...")

    processed_titles = {
        normalize_name(f)
        for f in os.listdir(clean_folder)
        if f.lower().endswith(".txt")
    }

    command = [
        "yt-dlp", *_LANG_ARGS, *_COOKIE_ARGS, *_EJS_ARGS,
        "--flat-playlist", "-i",
        "--print", "%(title)s|||%(id)s",
        channel_url,
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", env=_ENV
    )

    videos = []
    for line in result.stdout.splitlines():
        if "|||" not in line:
            continue
        title, vid = line.split("|||", 1)
        stem = sanitize_title(title.strip())
        if stem in processed_titles:
            continue
        videos.append((stem, vid.strip()))

    print(f"✅ 새로 수집할 영상 수: {len(videos)}개")
    return videos


# =========================
# 2. 자막 fetch → 정제 → 저장
# =========================
def fetch_subtitle(stem, video_id):
    """ko 자동자막 fetch → vtt_to_text → clean → clean_transcripts/<stem>.txt.
    성공 여부를 반환한다."""
    out_tmpl = os.path.join(sub_tmp_folder, "%(id)s.%(ext)s")
    command = [
        "yt-dlp", *_LANG_ARGS, *_COOKIE_ARGS, *_EJS_ARGS,
        "--write-auto-subs",
        "--sub-langs", "ko",
        "--sub-format", "vtt",
        "--skip-download",
        "-o", out_tmpl,
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    result = subprocess.run(
        command, env=_ENV, capture_output=True, text=True, encoding="utf-8"
    )

    vtt_path = os.path.join(sub_tmp_folder, f"{video_id}.ko.vtt")
    if not os.path.exists(vtt_path):
        print(f"  ⚠️ ko 자막 없음 — 건너뜀: {stem[:45]}")
        # CI 진단용: yt-dlp 의 마지막 몇 줄을 같이 출력해 원인 식별을 돕는다
        # (예: 데이터센터 IP 차단 시 YouTube 가 sign-in/consent 페이지 반환).
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-5:]
        for ln in tail:
            print(f"    [yt-dlp] {ln}")
        return False

    text = clean(vtt_to_text(vtt_path))
    out_path = os.path.join(clean_folder, stem + ".txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    os.remove(vtt_path)
    return True


# =========================
# 전체 실행
# =========================
if __name__ == "__main__":
    videos = list_unprocessed_videos()

    ok = 0
    for idx, (stem, vid) in enumerate(videos, 1):
        print(f"[{idx}/{len(videos)}] 📝 자막 수집: {stem[:45]}")
        if fetch_subtitle(stem, vid):
            ok += 1

    print(f"\n🎉 자막 수집 완료: {ok}/{len(videos)}개 → {clean_folder}/")
    print("다음 단계: python correct_transcripts.py  →  python generate_embeddings.py")

    # listing 에 잡힌 영상 중 일부라도 자막 fetch 에 실패했으면 워크플로를
    # 명시적으로 실패시킨다. 그래야 GH Actions 가 빨간 X 로 마킹되고
    # repo owner 에게 자동 알림 메일이 발송된다(silent fail 방지).
    # 새 영상이 0개인 경우(휴가 등)는 정상 종료.
    if videos and ok < len(videos):
        print(
            f"⚠️ {len(videos) - ok}개 영상 자막 fetch 실패 — 워크플로 실패 처리 "
            "(알림 발송용)"
        )
        sys.exit(1)
