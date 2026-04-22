# 📚 Research Paper Bot

  매주 최신 논문을 추천하고, Zotero에 저장된 논문을 요약해서 일주일에 한번씩 Discord로 보내는 개인용 봇 모음입니다.

  ---

  ## 🤖 Bots

  ### 1. 📅 Weekly Paper Bot
  관심 주제와 관련된 최신 논문을 찾아 선별한 뒤 Discord로 전송합니다.

  **동작 방식**
  1. 주제별로 `arXiv` + `OpenAlex` 에서 논문 검색
  2. 이미 본 논문 제외 (`seen_papers.json`)
  3. `Groq (LLaMA 3.3)`가 관련성 높은 논문을 최대 2편 선별
  4. 선별된 논문을 한국어로 요약
  5. Discord로 전송

  **토픽 설정 방법**
  
  seed_keyword를 넣으면 AI가 검색용 세부 쿼리를 생성합니다.

```python
  TOPICS = [
      {
          "name": "Nonlinear Metasurface",
          "seed_keyword": "nonlinear metasurface",
          "include_terms": ["harmonic generation", "ultrafast", "nanophotonics"],
          "exclude_terms": ["acoustic", "microwave", "antenna"]
      }
  ]
```
  설명:

  - seed_keyword: 가장 큰 주제어
  - include_terms: 포함되면 좋은 방향
  - exclude_terms: 피하고 싶은 인접 분야

  ———

  ### 2. 📖 Zotero Reading Bot

  Zotero에 저장된 읽지 않은 논문을 골라 요약해 일주일에 2번씩 Discord로 전송합니다.

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
  - ZOTERO_USER_ID : Zotero API user ID (숫자로 되어있음)
  - ZOTERO_USERNAME : Zotero ID (숫자 아님)

  ### Additional Secrets

  - UNPAYWALL_EMAIL
      - optional
      - zotero_bot.py에서 Unpaywall OA PDF 탐색용
      - zotero_bot_gemini.py에서는 contact email 용도로도 사용 가능

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
```python
  ├── paper_bot.py
  ├── zotero_bot_gemini.py
  ├── seen_papers.json
  └── .github/
      └── workflows/
          ├── monday_bot.yml
          └── zotero_bot.yml
```
  필요한 workflow는 실제 운영하는 파일에 맞춰 선택해서 쓰면 됩니다.

  ———
  예시 실행 스케줄:

  - Weekly bot: 매주 월요일 오전 7시 KST
  - Zotero bot: 매주 화요일 / 목요일 오전 7시 KST
  예:

  - 월요일 오전 7시 KST → 0 22 * * 0
  - 화요일 오전 7시 KST → 0 22 * * 1
  - 목요일 오전 7시 KST → 0 22 * * 3
