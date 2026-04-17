# 📚 Weekly Paper Bot

매주 월요일 오전 10시(KST)에 최신 논문을 자동으로 검색하고 Discord로 전송하는 봇입니다.

## 동작 방식

1. 지정한 키워드로 **arXiv** + **OpenAlex** 에서 논문 검색
2. 이미 본 논문 제외 (`seen_papers.json` 기록)
3. **Groq (LLaMA 3.3)** 이 관련성 + 최신성 기준으로 최대 2편 선별
4. 선별된 논문 영어로 요약 후 **Discord** 로 전송

## 현재 검색 토픽

| 토픽 | 검색 쿼리 |
|------|----------|
| Metasurface Saturable Absorber | metasurface saturable absorber mode locking, metasurface fiber laser ultrafast, nonlinear metasurface passive mode locking laser |
| THz Metalens | THz metalens, THz metasurface, THz metalens design |
| Metasurface Fiber | metafiber, metasurface integrated fiber, metasurface fiber tip |

## 토픽/쿼리 수정 방법

`paper_bot.py` 상단의 `TOPICS` 리스트를 수정하면 됩니다:

```python
TOPICS = [
    {
        "name": "토픽 이름",
        "queries": [
            "검색 쿼리 1",
            "검색 쿼리 2",
            "검색 쿼리 3"
        ]
    },
    ...
]
```

## 사용 API

| API | 용도 | 비용 |
|-----|------|------|
| [arXiv API](https://arxiv.org/help/api) | 논문 검색 | 무료 |
| [OpenAlex API](https://openalex.org) | 논문 검색 | 무료 |
| [Groq API](https://console.groq.com) | 논문 선별 + 요약 | 무료 |
| Discord Webhook | 메시지 전송 | 무료 |

## GitHub Secrets 설정

| Secret 이름 | 설명 |
|------------|------|
| `GROQ_API_KEY` | Groq API 키 ([발급](https://console.groq.com)) |
| `DISCORD_WEBHOOK_URL` | Discord 웹훅 URL |

## 파일 구조

```
├── paper_bot.py          # 메인 봇 코드
├── seen_papers.json      # 이미 본 논문 링크 기록 (자동 업데이트)
└── .github/
    └── workflows/
        └── monday_bot.yml  # GitHub Actions 스케줄 설정
```

## 수동 실행

GitHub Actions 탭 → **Weekly Paper Bot** → **Run workflow** 클릭
