"""
batch_subs_update.py — 1년 정체 일괄 갱신용 임시 스크립트 (일회성)

clean_transcripts/ 최신 날짜(2025-04-06) 이후의 채널 영상을
YouTube 자동 자막으로 일괄 수집해 clean_transcripts/ 에 추가한다.

기존 update_transcribe_and_clean.py 는 손대지 않음 (자막 워크플로
영구화는 본 스크립트 결과 검증 후 별도로 결정).
"""
import os
import re
import sys
import subprocess
from datetime import date, datetime
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

CHANNEL_URL = "https://www.youtube.com/@centralchurch5467/videos"
CUTOFF_DATE = date(2025, 4, 7)
CLEAN_DIR = Path("clean_transcripts")
RAW_VTT_DIR = Path("auto_subs_raw")
LANG = "ko"

# yt-dlp 채널 listing 시 한국어 원본 제목 강제 (자동번역 회피)
YDL_LANG_ARGS = [
    "--extractor-args", "youtube:lang=ko",
    "--add-header", "Accept-Language:ko-KR,ko;q=0.9",
]


def run_ytdlp(args):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        ["yt-dlp", *YDL_LANG_ARGS, *args],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", env=env,
    )


def extract_date_from_title(title):
    m = re.search(r"(20\d{6})", title)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", title)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass
    return None


def normalize_filename(title):
    # MM/DD/YYYY → YYYYMMDD (영문 영상 잔재 대비)
    title = re.sub(
        r"(\d{1,2})/(\d{1,2})/(20\d{2})",
        lambda m: f"{int(m.group(3)):04d}{int(m.group(1)):02d}{int(m.group(2)):02d}",
        title,
    )
    # Windows 파일명 금지 문자
    title = title.replace(":", "_")
    title = re.sub(r'[<>"\\|?*]', "_", title)
    return title.strip()


def get_target_videos():
    print("[1/4] 채널 영상 목록 추출 중...")
    result = run_ytdlp([
        "--flat-playlist", "-i",
        "--print", "%(title)s|||%(webpage_url)s",
        CHANNEL_URL,
    ])
    videos = []
    for line in result.stdout.splitlines():
        if "|||" not in line:
            continue
        title, url = line.split("|||", 1)
        d = extract_date_from_title(title)
        if d and d >= CUTOFF_DATE:
            videos.append((d, title.strip(), url.strip()))
    videos.sort()
    return videos


def download_subs(url):
    before = set(RAW_VTT_DIR.glob("*.vtt"))
    run_ytdlp([
        "--write-auto-subs",
        "--sub-lang", LANG,
        "--skip-download",
        "-o", str(RAW_VTT_DIR / "%(title)s.%(ext)s"),
        url,
    ])
    after = set(RAW_VTT_DIR.glob("*.vtt"))
    new = after - before
    return next(iter(new)) if new else None


def vtt_to_text(vtt_path):
    content = vtt_path.read_text(encoding="utf-8")
    out = []
    for line in content.split("\n"):
        if re.search(r"<\d+:\d+", line) or "<c>" in line:
            cleaned = re.sub(r"<[^>]+>", "", line).strip()
            if cleaned:
                out.append(cleaned)
    return "\n".join(out)


def clean_text(text):
    # 기존 update_transcribe_and_clean.py 와 동일 규칙
    text = re.sub(r"\b(할렐루야|아멘|맞죠|그러니까요|뭐예요|그렇죠|여러분)\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.!?])", r"\1\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text


def main():
    RAW_VTT_DIR.mkdir(exist_ok=True)
    CLEAN_DIR.mkdir(exist_ok=True)

    videos = get_target_videos()
    print(f"     처리 대상: {len(videos)}개\n")

    print("[2/4] 자동 자막 일괄 다운로드 + 변환...")
    success, skip, fail = 0, 0, 0
    for i, (d, title, url) in enumerate(videos, 1):
        norm_title = normalize_filename(title)
        out_path = CLEAN_DIR / f"{norm_title}.txt"
        if out_path.exists():
            print(f"  [{i:>2}/{len(videos)}] SKIP (이미 있음): {title[:60]}")
            skip += 1
            continue

        print(f"  [{i:>2}/{len(videos)}] DL  {d}  {title[:60]}")
        try:
            vtt = download_subs(url)
            if vtt is None or not vtt.exists():
                print(f"             ⚠ 자막 없음")
                fail += 1
                continue
            text = clean_text(vtt_to_text(vtt))
            out_path.write_text(text, encoding="utf-8")
            success += 1
        except Exception as e:
            print(f"             ⚠ ERROR: {e}")
            fail += 1

    print()
    print(f"[3/4] 완료: 성공 {success}, 스킵 {skip}, 실패 {fail}")
    print(f"[4/4] 다음 단계 — python generate_embeddings.py")


if __name__ == "__main__":
    main()
