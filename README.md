# 📚 Research Paper Bot

  매주 최신 논문을 추천하고, Zotero에 저장된 논문을 요약해서 Discord로 보내는 개인용 봇 모음입니다.

  ---

  ## 🤖 Bots

  ### 1. 📅 Weekly Paper Bot
  관심 주제와 관련된 최신 논문을 찾아 선별한 뒤 Discord로 전송합니다.

  지원 버전:
  - `paper_bot.py`
    - 검색 쿼리를 직접 지정하는 버전
  - `paper_bot_ai_queries.py`
    - 큰 주제어(`seed_keyword`)를 넣으면 AI가 세부 검색 쿼리를 생성하는 버전

  **동작 방식**
  1. 주제별로 `arXiv` + `OpenAlex` 에서 논문 검색
  2. 이미 본 논문 제외 (`seen_papers.json`)
  3. `Groq (LLaMA 3.3)`가 관련성 높은 논문을 최대 2편 선별
  4. 선별된 논문을 한국어로 요약
  5. Discord로 전송

  **토픽 설정 방법**

  ### Manual Query Version
  `paper_bot.py`에서는 `TOPICS`에 `queries`를 직접 넣습니다.

  ```python
  TOPICS = [
      {
          "name": "THz Metalens",
          "queries": [
              "THz metalens",
              "THz metasurface",
              "THz metalens design"
          ]
      }
  ]

  ### AI Query Expansion Version

  paper_bot_ai_queries.py에서는 seed_keyword를 넣으면 AI가 검색용 세부 쿼리를 생성합니다.

  TOPICS = [
      {
          "name": "Nonlinear Metasurface",
          "seed_keyword": "nonlinear metasurface",
          "include_terms": ["harmonic generation", "ultrafast", "nanophotonics"],
          "exclude_terms": ["acoustic", "microwave", "antenna"]
      }
  ]

  설명:

  - seed_keyword: 가장 큰 주제어
  - include_terms: 포함되면 좋은 방향
  - exclude_terms: 피하고 싶은 인접 분야

  ———

  ### 2. 📖 Zotero Reading Bot

  Zotero에 저장된 읽지 않은 논문을 골라 요약해 Discord로 전송합니다.

  지원 버전:

  - zotero_bot.py
      - PDF 원문까지 시도하는 Groq 버전
  - zotero_bot_gemini.py
      - 초록 중심으로 요약하는 Gemini 버전

  #### zotero_bot.py

  동작 방식

  1. Zotero에서 BOT 태그가 없는 논문 중 1편 선택
  2. 가능한 경우 원문 PDF를 우선 시도
      - Zotero attachment PDF
      - direct PDF URL
      - arXiv PDF
      - PubMed Central PDF
      - Unpaywall OA PDF
  3. 원문 확보에 실패하면 초록으로 요약
  4. Discord로 전송
  5. Zotero에 BOT 태그 자동 추가
  6. 논문 링크 + Zotero 웹 링크 전송

  #### zotero_bot_gemini.py

  동작 방식

  1. Zotero에서 BOT 태그가 없는 논문 중 1편 선택
  2. Zotero 초록이 있으면 초록으로 요약
  3. Zotero 초록이 없으면 Crossref 또는 OpenAlex에서 온라인 초록 조회
  4. 초록 기반으로 Gemini가 상세 요약
  5. Discord로 전송
  6. Zotero에 BOT 태그 자동 추가
  7. 논문 링크 + Zotero 웹 링크 전송

  ———

  ## 🔑 GitHub Secrets

  ### Weekly Paper Bot

  - GROQ_API_KEY
  - DISCORD_WEBHOOK_URL

  ### Zotero Bot

  - ZOTERO_DISCORD_WEBHOOK_URL
  - ZOTERO_API_KEY
  - ZOTERO_USER_ID
  - ZOTERO_USERNAME

  ### Additional Secrets

  - UNPAYWALL_EMAIL
      - optional
      - zotero_bot.py에서 Unpaywall OA PDF 탐색용
      - zotero_bot_gemini.py에서는 contact email 용도로도 사용 가능

  ### Model-Specific Secrets

  - GROQ_API_KEY
      - paper_bot.py
      - paper_bot_ai_queries.py
      - zotero_bot.py
  - GEMINI_API_KEY
      - zotero_bot_gemini.py
  - GEMINI_MODEL
      - optional
      - default: gemini-2.5-flash

  ———

  ## 🛠️ APIs Used

  | API | Usage | Cost |
  |-----|------|------|
  | arXiv API (https://export.arxiv.org/api/help) | 논문 검색 | 무료 |
  | OpenAlex API (https://developers.openalex.org/) | 논문 검색 / 초록 조회 | 무료 |
  | Crossref API (https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | DOI 기반 초록 조회 | 무료 |
  | Groq API (https://console.groq.com/docs) | 쿼리 생성 / 논문 선별 / 요약 | 무료 또는 사용량 기반 |
  | Gemini API (https://ai.google.dev/gemini-api/docs) | Zotero 초록 요약 | 무료 또는 사용량 기반 |
  | Zotero API (https://www.zotero.org/support/dev/web_api/v3/start) | 논문 목록 조회 / 태그 관리 | 무료 |
  | Discord Webhook | 메시지 전송 | 무료 |

  ———

  ## 📁 File Structure

  ├── paper_bot.py
  ├── paper_bot_ai_queries.py
  ├── zotero_bot.py
  ├── zotero_bot_gemini.py
  ├── seen_papers.json
  └── .github/
      └── workflows/
          ├── weekly_paper_bot.yml
          ├── weekly_paper_bot_ai.yml
          ├── zotero_bot.yml
          └── zotero_bot_gemini.yml

  필요한 workflow는 실제 운영하는 파일에 맞춰 선택해서 쓰면 됩니다.

  ———

  ## ▶️ Run Locally

  ### Weekly Paper Bot

  python paper_bot.py

  ### Weekly Paper Bot with AI Query Expansion

  python paper_bot_ai_queries.py

  ### Zotero Bot (Groq)

  python zotero_bot.py

  ### Zotero Bot (Gemini)

  python zotero_bot_gemini.py

  ———

  ## ▶️ Run with GitHub Actions

  - Weekly bot:
      - GitHub Actions 탭에서 해당 workflow 선택
      - Run workflow
  - Zotero bot:
      - GitHub Actions 탭에서 해당 workflow 선택
      - Run workflow

  예시 실행 스케줄:

  - Weekly bot: 매주 월요일 오전 7시 KST
  - Zotero bot: 매주 화요일 / 목요일 오전 7시 KST

  주의:

  - GitHub Actions cron은 UTC 기준입니다.
  - KST 오전 7시는 UTC 전날 22:00입니다.

  예:

  - 월요일 오전 7시 KST → 0 22 * * 0
  - 화요일 오전 7시 KST → 0 22 * * 1
  - 목요일 오전 7시 KST → 0 22 * * 3

  ———

  ## 📝 Notes

  - ZOTERO_USER_ID는 Zotero API용 숫자 ID입니다.
  - ZOTERO_USERNAME은 Zotero 웹 링크 생성용 사용자명입니다.
  - citation key는 Zotero 웹 URL 식별자가 아닙니다.
  - zotero_bot_gemini.py는 현재 PDF 본문을 읽지 않고 초록만 기반으로 요약합니다.
  - paper_bot_ai_queries.py는 자동 쿼리 생성 버전이지만, 너무 넓은 주제어는 여전히 잡음을 만들 수 있으므로 include_terms와
    exclude_terms를 같이 조정하는 것이 좋습니다.
