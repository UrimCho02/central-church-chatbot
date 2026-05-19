import os
import subprocess
import time
import whisper
import re

# =========================
# 경로 설정
# =========================
channel_url = "https://www.youtube.com/@centralchurch5467/videos"

download_folder = "downloads"
transcript_folder = "transcripts"
clean_folder = "clean_transcripts"

os.makedirs(download_folder, exist_ok=True)
os.makedirs(transcript_folder, exist_ok=True)
os.makedirs(clean_folder, exist_ok=True)

def normalize_name(name):
    return os.path.splitext(name)[0].strip()

# =========================
# 1. 유튜브 영상 URL 목록 추출
# =========================
def extract_youtube_urls():
    output_file = "urls_to_download.txt"

    print("🌐 유튜브 영상 목록 확인 중...")

    # 이미 전처리 완료된 설교 제목 목록
    processed_titles = {
        normalize_name(f)
        for f in os.listdir(clean_folder)
        if f.lower().endswith(".txt")
    }

    # 유튜브 채널 영상 목록: 제목 + URL 추출
    command = [
        "yt-dlp",
        "--flat-playlist",
        "-i",
        "--print",
        "%(title)s|||%(webpage_url)s",
        channel_url
    ]

    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

    urls_to_download = []

    for line in result.stdout.splitlines():
        if "|||" not in line:
            continue

        title, url = line.split("|||", 1)
        title = title.strip()
        url = url.strip()

        if title not in processed_titles:
            urls_to_download.append(url)

    with open(output_file, "w", encoding="utf-8") as f:
        for url in urls_to_download:
            f.write(url + "\n")

    print(f"✅ 새로 다운로드할 영상 수: {len(urls_to_download)}개")
    print(f"✅ 다운로드 대상 URL이 {output_file}에 저장되었습니다!")


# =========================
# 2. m4a 오디오 다운로드
# =========================
def download_audio_m4a():
    if not os.path.exists("urls_to_download.txt") or os.path.getsize("urls_to_download.txt") == 0:
        print("⚠️ urls.txt 파일이 없습니다. URL 추출부터 확인하세요.")
        return

    print("📥 유튜브 오디오 다운로드 시작...")

    command = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--extract-audio",
        "--audio-format", "m4a",
        "--audio-quality", "192K",
        "--download-archive", "downloaded.txt",
        "--continue",
        "--no-overwrites",
        "--dateafter", "20250408",
        "-o", os.path.join(download_folder, "%(title)s.%(ext)s"),
        "-a", "urls_to_download.txt"
    ]

    subprocess.run(command)
    print("✅ 유튜브 오디오 다운로드 완료!")


# =========================
# 3. 아직 STT 안 된 m4a 파일 찾기
# =========================
def get_unprocessed_audio_files():
    audio_files = [
        f for f in os.listdir(download_folder)
        if f.lower().endswith((".m4a", ".mp4", ".webm", ".mp3"))
    ]

    txt_files = [
        os.path.splitext(f)[0]
        for f in os.listdir(transcript_folder)
        if f.lower().endswith(".txt")
    ]

    new_files = [
        f for f in audio_files
        if os.path.splitext(f)[0] not in txt_files
    ]

    return new_files


# =========================
# 4. Whisper STT
# =========================
def transcribe_files(files):
    if not files:
        print("✅ STT 변환할 새 오디오 파일이 없습니다.")
        return

    print(f"🧠 STT 변환할 파일 수: {len(files)}개")
    model = whisper.load_model("medium")

    start_all = time.time()

    for idx, file in enumerate(files):
        audio_path = os.path.join(download_folder, file)
        txt_filename = os.path.splitext(file)[0] + ".txt"
        txt_path = os.path.join(transcript_folder, txt_filename)

        print(f"\n[{idx + 1}/{len(files)}] 🎧 STT 변환 중: {file}")
        start = time.time()

        result = model.transcribe(audio_path, fp16=False)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result["text"])

        elapsed = time.time() - start
        print(f"✅ STT 완료: {txt_filename} (⏱ {elapsed:.2f}초)")

        # STT 완료 후 원본 오디오 파일 삭제
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"🗑️ 원본 오디오 삭제 완료: {file}")

    total = time.time() - start_all
    print(f"\n🔥 전체 STT 완료! 총 소요 시간: {total:.2f}초")


# =========================
# 5. 전처리
# =========================
def clean_text(text):
    text = re.sub(r"\b(할렐루야|아멘|맞죠|그러니까요|뭐예요|그렇죠|여러분)\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.!?])", r"\1\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text


def clean_transcripts():
    print("\n✨ 전처리 시작...")

    cleaned_count = 0

    for file in os.listdir(transcript_folder):
        if not file.lower().endswith(".txt"):
            continue

        input_path = os.path.join(transcript_folder, file)
        output_path = os.path.join(clean_folder, file)

        if os.path.exists(output_path):
            continue

        with open(input_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        cleaned = clean_text(raw_text)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        cleaned_count += 1
        print(f"✅ 전처리 완료: {file}")

    if cleaned_count == 0:
        print("✅ 새로 전처리할 파일이 없습니다.")
    else:
        print(f"🎉 전처리 완료 파일 수: {cleaned_count}개")


# =========================
# 전체 실행
# =========================
if __name__ == "__main__":
    print("🌐 유튜브 영상 URL 추출 시작...")
    extract_youtube_urls()

    print("\n📥 m4a 오디오 다운로드 시작...")
    download_audio_m4a()

    print("\n🔍 새 STT 대상 파일 탐색 중...")
    new_files = get_unprocessed_audio_files()
    transcribe_files(new_files)

    clean_transcripts()

    print("\n🎉 전체 작업 완료!")