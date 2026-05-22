# -*- coding: utf-8 -*-
"""
설교 전사본 LLM 교정 패스.

clean_transcripts/ 의 자동전사본을 읽어 STT 오류(신앙 어휘/고유명사 오인식)를
교정한 뒤 corrected_transcripts/ 에 저장한다. 원본은 건드리지 않는다.

- 긴 본문은 줄 단위로 ~3000자 배치로 나눠 교정(출력 잘림 방지).
- 이미 교정된 파일은 건너뛴다(재실행/중단 복구 가능).
- 교정 전후 길이비를 출력해 요약·삭제 사고를 감지한다.

사용법:
  python correct_transcripts.py                # 전체 263개
  python correct_transcripts.py "파일명1.txt" "파일명2.txt"   # 지정 파일만(샘플)
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

IN_DIR = "clean_transcripts"
OUT_DIR = "corrected_transcripts"
MODEL = os.getenv("CORRECT_MODEL", "gpt-4o-mini")
BATCH_CHARS = 3000
WORKERS = 8  # 파일 단위 동시 처리 수

SYSTEM = "당신은 한국어 개신교 설교 자동전사본의 교정 전문가입니다. 음성인식(STT) 오류만 바로잡습니다."

INSTRUCT = """아래는 한국어 개신교 설교의 자동 음성인식 전사본 일부입니다. STT가 신앙 어휘·성경 인명/지명·고유명사를 잘못 알아들은 오류가 많습니다. 다음 규칙대로 교정하세요.

규칙:
1. 명백한 전사 오류만 바로잡는다. 예: "11조"→"십일조", "9약"→"구약", "방군의 여우와"→"만군의 여호와", "신약선경"→"신약성경", "바리세인"→"바리새인", "서위관"→"서기관", "마테복음"→"마태복음", "하얄"→"할례".
2. 성경 구절 인용은 개역개정 표현에 맞게 자연스럽게 바로잡는다.
3. 원문의 내용·의미·순서·분량을 그대로 유지한다. 요약·삭제·문장 재작성·새 내용 추가를 절대 하지 않는다.
4. 설교자의 구어체 말투·반복·군더더기는 그대로 둔다.
5. 확신이 없으면 원문을 그대로 둔다.

교정된 본문만 출력하세요. 설명·머리말·따옴표 없이.

[전사본]
"""


def batches(text):
    """줄 단위로 ~BATCH_CHARS 크기의 배치로 분할."""
    out, cur = [], ""
    for line in text.splitlines(keepends=True):
        if cur and len(cur) + len(line) > BATCH_CHARS:
            out.append(cur)
            cur = ""
        cur += line
    if cur:
        out.append(cur)
    return out


def is_degenerate(out, src):
    """LLM이 반복 루프에 빠졌는지 판정."""
    if len(out) > 1.5 * len(src) + 200:
        return True
    toks = out.split()
    run = 1
    for i in range(1, len(toks)):
        run = run + 1 if toks[i] == toks[i - 1] else 1
        if run >= 12:
            return True
    return False


def correct_batch(text):
    for attempt in range(4):
        try:
            r = client.chat.completions.create(
                model=MODEL,
                temperature=0 if attempt == 0 else 0.3,  # 재시도 시 루프 탈출용
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": INSTRUCT + text},
                ],
            )
            out = r.choices[0].message.content
            if not is_degenerate(out, text):
                return out
            print(f"    반복 루프 감지 - 재시도 {attempt + 1}/4")
        except Exception as e:
            print(f"    재시도 {attempt + 1}/4: {e}")
            time.sleep(5)
    # 4회 모두 실패: 루프 폭발본보다 미교정 원문이 안전
    print("    교정 실패 - 해당 배치 원문 유지")
    return text


def process_file(fn):
    """파일 1개 교정. 배치는 순서 유지를 위해 파일 내에서는 순차 처리."""
    src = open(os.path.join(IN_DIR, fn), encoding="utf-8").read()
    bs = batches(src)
    corrected = "".join(correct_batch(b) for b in bs)
    ratio = len(corrected) / len(src) if src else 1
    with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8") as f:
        f.write(corrected)
    flag = "  ⚠️ 길이변화 큼 — 검토 필요" if not (0.85 <= ratio <= 1.15) else ""
    return f"{fn[:45]} ({len(src)}->{len(corrected)}자, 비 {ratio:.2f}){flag}"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    args = sys.argv[1:]
    files = args if args else sorted(f for f in os.listdir(IN_DIR) if f.endswith(".txt"))
    todo = [f for f in files if not os.path.exists(os.path.join(OUT_DIR, f))]
    print(f"모델 {MODEL} / 대상 {len(files)}개 / 교정 필요 {len(todo)}개 / 동시 {WORKERS}")

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(process_file, fn): fn for fn in todo}
        for fut in as_completed(futs):
            done += 1
            try:
                print(f"[{done}/{len(todo)}] {fut.result()}")
            except Exception as e:
                print(f"[{done}/{len(todo)}] 실패: {futs[fut][:45]} - {e}")

    print("[OK] 교정 패스 종료")


if __name__ == "__main__":
    main()
