# -*- coding: utf-8 -*-
"""
YouTube 자동자막 VTT → 평문 텍스트.

YouTube auto-sub VTT 특성:
- 롤링 방식이라 직전 줄이 다음 cue 상단에 중복으로 반복된다.
- 단어별 타이밍 태그(<00:00:02.480><c> 말씀</c>)가 본문에 섞여 있다.
- align/position 등 cue 설정이 붙는다.

이 스크립트는 위를 모두 제거하고, 중복 없는 평문 한 덩어리를 만든다.
"""
import re
import sys


def vtt_to_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # 인라인 타이밍 태그 <...> 및 <c>...</c> 제거
    raw = re.sub(r"<[^>]+>", "", raw)

    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "WEBVTT" or line.startswith(("Kind:", "Language:")):
            continue
        # 타임스탬프 cue 줄 (00:00:02.159 --> ...) 제거
        if "-->" in line:
            continue
        lines.append(line)

    # 롤링 중복 제거: 직전에 출력한 줄과 동일하면 건너뛴다.
    deduped = []
    for line in lines:
        if deduped and deduped[-1] == line:
            continue
        deduped.append(line)

    # cue 단위로 줄을 유지한다(correct_transcripts.py 가 줄 단위로 배치 분할하므로).
    return "\n".join(deduped)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    text = vtt_to_text(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[OK] {out} ({len(text)}자)")
    else:
        print(text)
