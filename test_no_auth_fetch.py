# -*- coding: utf-8 -*-
"""
쿠키 없이 YouTube 한국어 자막을 fetch 할 수 있는지 확인하는 스모크 테스트.

배경: 기존 파이프라인은 yt-dlp + 로그인 쿠키로 자막을 받는다. GH Actions
데이터센터 IP는 YouTube 봇 체크에 걸려 쿠키 없이는 실패. 쿠키를 새로
발급하려 했으나 신규 계정이 반복 정지 → 쿠키 우회 자체를 대체할
경로 탐색.

이 스크립트는 두 가지를 확인한다:
  1) `youtube-transcript-api` (public timedtext 엔드포인트) 가 GH Actions
     IP 에서 응답하는가?
  2) 참고용으로 raw yt-dlp 도 쿠키 없이 시도 (이건 예상대로 실패할 것).

사용법:
  python test_no_auth_fetch.py <video_id_or_url>
"""
import re
import subprocess
import sys


def extract_video_id(arg: str) -> str:
    """URL 이든 ID 든 11자 영상 ID 로 정규화."""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/watch/)([\w-]{11})", arg)
    if m:
        return m.group(1)
    if re.fullmatch(r"[\w-]{11}", arg):
        return arg
    raise SystemExit(f"영상 ID 인식 실패: {arg!r}")


def try_transcript_api(vid: str) -> None:
    print("\n===== [A] youtube-transcript-api (no auth) =====")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as e:
        print(f"  ⚠️ 라이브러리 import 실패: {e}")
        return

    try:
        # 신·구 API 모두 커버 (v0.6.x: get_transcript, v1.x: fetch)
        if hasattr(YouTubeTranscriptApi, "fetch"):
            api = YouTubeTranscriptApi()
            fetched = api.fetch(vid, languages=["ko"])
            snippets = list(fetched)
            get_text = lambda s: s.text
        else:
            snippets = YouTubeTranscriptApi.get_transcript(vid, languages=["ko"])
            get_text = lambda s: s["text"]
    except Exception as e:
        print(f"  ❌ 실패: {type(e).__name__}: {e}")
        return

    if not snippets:
        print("  ⚠️ 결과 비어있음")
        return

    total_chars = sum(len(get_text(s)) for s in snippets)
    print(f"  ✅ 성공: {len(snippets)} cues, 총 {total_chars}자")
    print("  --- 앞부분 미리보기 ---")
    preview = " ".join(get_text(s) for s in snippets[:10])
    print(f"  {preview[:300]}")


def try_ytdlp_no_cookies(vid: str) -> None:
    print("\n===== [B] yt-dlp (no cookies, 참고용) =====")
    cmd = [
        "yt-dlp",
        "--write-auto-subs", "--sub-langs", "ko", "--sub-format", "vtt",
        "--skip-download",
        "--simulate",
        "-o", "/tmp/%(id)s.%(ext)s",
        f"https://www.youtube.com/watch?v={vid}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        print("  ⚠️ yt-dlp 미설치")
        return
    except subprocess.TimeoutExpired:
        print("  ❌ 타임아웃(60s)")
        return

    print(f"  exit={result.returncode}")
    tail = (result.stderr or result.stdout or "").strip().splitlines()[-6:]
    for ln in tail:
        print(f"    {ln}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        raise SystemExit("사용법: python test_no_auth_fetch.py <video_id_or_url>")
    vid = extract_video_id(sys.argv[1])
    print(f"대상 영상 ID: {vid}")
    try_transcript_api(vid)
    try_ytdlp_no_cookies(vid)
