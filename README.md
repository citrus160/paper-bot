# 📚 Research Paper Bot

매주 자동으로 최신 논문을 추천하고, Zotero에 쌓인 논문을 요약해주는 봇입니다.

---

## 🤖 봇 종류

### 1. 📅 Weekly Paper Bot (월요일 오전 7시 KST)
최신 논문을 자동으로 검색하고 선별해서 Discord로 전송합니다.

**동작 방식:**
1. 지정한 키워드로 **arXiv** + **OpenAlex** 에서 논문 검색
2. 이미 본 논문 제외 (`seen_papers.json` 기록)
3. **Groq (LLaMA 3.3)** 이 관련성 + 최신성 기준으로 최대 2편 선별
4. 선별된 논문 영어로 요약 후 **Discord** 로 전송

**현재 검색 토픽:**

| 토픽 | 검색 쿼리 |
|------|----------|
| Metasurface Saturable Absorber | metasurface saturable absorber mode locking, metasurface fiber laser ultrafast, nonlinear metasurface passive mode locking laser |
| THz Metalens | THz metalens, THz metasurface, THz metalens design |
| Metasurface Fiber | metafiber, metasurface integrated fiber, metasurface fiber tip |

**토픽/쿼리 수정 방법:**

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

---

### 2. 📖 Zotero Reading Bot (화/목 오전 10시 KST)
Zotero에 저장된 읽지 않은 논문을 랜덤으로 1편 골라 요약해줍니다.

**동작 방식:**
1. Zotero에서 `BOT` 태그 없는 논문 중 랜덤 1편 선택
2. arXiv 논문이면 **PDF 원문** 읽고 요약
3. 아니면 **초록**으로 요약
4. 초록도 없으면 **DOI/URL로 웹 크롤링** 후 요약
5. Discord로 전송 (별도 채널)
6. Zotero에 `BOT` 태그 자동 추가

---

## 🔑 GitHub Secrets 설정

| Secret 이름 | 설명 |
|------------|------|
| `GROQ_API_KEY` | Groq API 키 ([발급](https://console.groq.com)) |
| `DISCORD_WEBHOOK_URL` | Discord 웹훅 URL (논문 추천 채널) |
| `ZOTERO_DISCORD_WEBHOOK_URL` | Discord 웹훅 URL (Zotero 읽기 채널) |
| `ZOTERO_API_KEY` | Zotero API 키 ([발급](https://www.zotero.org/settings/keys)) |
| `ZOTERO_USER_ID` | Zotero User ID ([확인](https://www.zotero.org/settings/keys)) |

---

## 🛠️ 사용 API

| API | 용도 | 비용 |
|-----|------|------|
| [arXiv API](https://arxiv.org/help/api) | 논문 검색 | 무료 |
| [OpenAlex API](https://openalex.org) | 논문 검색 | 무료 |
| [Groq API](https://console.groq.com) | 논문 선별 + 요약 | 무료 |
| [Zotero API](https://www.zotero.org/support/dev/web_api/v3/start) | 논문 목록 + 태그 관리 | 무료 |
| Discord Webhook | 메시지 전송 | 무료 |

---

## 📁 파일 구조

```
├── paper_bot.py            # 논문 추천 봇
├── zotero_bot.py           # Zotero 읽기 봇
├── seen_papers.json        # 이미 본 논문 링크 기록 (자동 업데이트)
└── .github/
    └── workflows/
        ├── monday_bot.yml      # 매주 월요일 실행
        └── zotero_bot.yml      # 매주 화/목 실행
```

---

## ▶️ 수동 실행

- **논문 추천**: GitHub Actions 탭 → **Weekly Paper Bot** → **Run workflow**
- **Zotero 읽기**: GitHub Actions 탭 → **Zotero Reading Bot** → **Run workflow**
