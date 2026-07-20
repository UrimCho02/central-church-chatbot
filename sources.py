# -*- coding: utf-8 -*-
"""수집 대상 채널·플레이리스트 정의.

각 소스는:
- name:   파이프라인 로그/식별용 (파일에는 안 들어감)
- url:    yt-dlp 가 훑을 채널 or 플레이리스트 URL
- prefix: clean_transcripts 파일명 앞에 붙일 라벨 (None 이면 붙이지 않음)

기존 센트럴처치는 prefix 없이 원본 파일명 규칙을 그대로 유지한다 —
262+ 개 파일이 이미 그 규칙으로 저장돼 있어 파일명을 새로 부여하면 재임베딩이
필요해지기 때문. 새로 추가하는 만나 시리즈에만 [만나] prefix 를 붙인다.

만나교회(김병삼 목사) 최근 5년(2022~2026) 예배시리즈 + 변화산 부흥회
플레이리스트 24개. 담임 목사 강해 위주만 선정. 찬양·컨퍼런스·인터뷰·해외
콘텐츠·주중/토요예배·숏츠 등은 제외.
"""

_MANNA_PL = "https://www.youtube.com/playlist?list="

SOURCES = [
    {
        "name": "centralchurch",
        "url": "https://www.youtube.com/@centralchurch5467/videos",
        "prefix": None,
    },
    # -------- 만나교회 2026 --------
    # NOTE(2026-07-15): 센트럴 미적재 4건(06-21/28, 07-05/12) 캐치업 위해 임시 주석.
    # 만나 백필 실행 위치 결정되면 원복. 관련: memory manna-backfill-2026-07.
    # {"name": "manna_2026_jachi",       "url": _MANNA_PL + "PLdMv0JwvPIiAKoVAkm0Xa_Rt_5HbfZSwK", "prefix": "[만나]"},
    # {"name": "manna_2026_1_byeonhwa",  "url": _MANNA_PL + "PLdMv0JwvPIiD3dNsbKCuIO5C9t9sB7bTE", "prefix": "[만나]"},
    {"name": "manna_2026_belief",      "url": _MANNA_PL + "PLdMv0JwvPIiA3h3fa0I32Ni6azfkJSBig", "prefix": "[만나]"},
    # -------- 만나교회 2025 --------
    # {"name": "manna_2025_2_byeonhwa",  "url": _MANNA_PL + "PLdMv0JwvPIiAFwlr4nTs7hbPmgJaw9SxL", "prefix": "[만나]"},
    # {"name": "manna_2025_myeongjak",   "url": _MANNA_PL + "PLdMv0JwvPIiAxGAE2JHmEnpwDFM6umUi5", "prefix": "[만나]"},
    # {"name": "manna_2025_haengjeon",   "url": _MANNA_PL + "PLdMv0JwvPIiCxGF8axV1ZrCvQmYtDxNil", "prefix": "[만나]"},
    # {"name": "manna_2025_1_byeonhwa",  "url": _MANNA_PL + "PLdMv0JwvPIiAioPjhipBGg8UoLD77HogU", "prefix": "[만나]"},
    # {"name": "manna_2025_anyeseo",     "url": _MANNA_PL + "PLdMv0JwvPIiCZJkt3lpFMIUmYTQxI996x", "prefix": "[만나]"},
    # -------- 만나교회 2024 --------
    # {"name": "manna_2024_maeum",       "url": _MANNA_PL + "PLdMv0JwvPIiBoN3hAPTt1nlgqq7wY5deN", "prefix": "[만나]"},
    # {"name": "manna_2024_yeolgwang",   "url": _MANNA_PL + "PLdMv0JwvPIiCRslYfpC6sg6OkxGQVFXJ5", "prefix": "[만나]"},
    # {"name": "manna_2024_1_byeonhwa",  "url": _MANNA_PL + "PLdMv0JwvPIiDZ1zguNnydau0X86VvS8s4", "prefix": "[만나]"},
    # {"name": "manna_2024_hanim",       "url": _MANNA_PL + "PLdMv0JwvPIiAeyvFxosVtiesjENahi8dN", "prefix": "[만나]"},
    # -------- 만나교회 2023 --------
    # {"name": "manna_2023_elijah",      "url": _MANNA_PL + "PLdMv0JwvPIiDUlaaxG4vnTs6393j-n754", "prefix": "[만나]"},
    # {"name": "manna_2023_2_byeonhwa",  "url": _MANNA_PL + "PLdMv0JwvPIiB7QhfQoAcLvIq1QDPDZFGo", "prefix": "[만나]"},
    # {"name": "manna_2023_gyeolsim",    "url": _MANNA_PL + "PLdMv0JwvPIiCACs9CtXtBw_K2VcOecL-K", "prefix": "[만나]"},
    # {"name": "manna_2023_kkumkkuneun", "url": _MANNA_PL + "PLdMv0JwvPIiAvkLNulen3CVO6D8aFbFfm", "prefix": "[만나]"},
    # {"name": "manna_2023_1_byeonhwa",  "url": _MANNA_PL + "PLdMv0JwvPIiBkyh_NOAN1ynWTyGRCcVKC", "prefix": "[만나]"},
    # {"name": "manna_2023_seupgwan",    "url": _MANNA_PL + "PLdMv0JwvPIiCHAjGkOXojVYRWgqLaE1UK", "prefix": "[만나]"},
    # -------- 만나교회 2022 --------
    # {"name": "manna_2022_apeseo_2",    "url": _MANNA_PL + "PLdMv0JwvPIiDLbXV5dTRnaPtaEVJr3yPM", "prefix": "[만나]"},
    # {"name": "manna_2022_naneun",      "url": _MANNA_PL + "PLdMv0JwvPIiDuj3oPcVsvAZyfuTZKaex-", "prefix": "[만나]"},
    # {"name": "manna_2022_2_byeonhwa",  "url": _MANNA_PL + "PLdMv0JwvPIiAN_XpRdiF9ANPehDeGWbQo", "prefix": "[만나]"},
    # {"name": "manna_2022_gil",         "url": _MANNA_PL + "PLdMv0JwvPIiCAm3ZzEcdkqIQRSqpJK65d", "prefix": "[만나]"},
    # {"name": "manna_2022_1_kido",      "url": _MANNA_PL + "PLdMv0JwvPIiDPrEJ68HvZ8C5hkiO2rtkR", "prefix": "[만나]"},
    # {"name": "manna_2022_apeseo_1",    "url": _MANNA_PL + "PLdMv0JwvPIiBScfjmdmq_65aJvK6-7tNf", "prefix": "[만나]"},
]
