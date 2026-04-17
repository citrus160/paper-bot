import os
import requests
import xml.etree.ElementTree as ET
import time
import asyncio
import aiohttp

import google.generativeai as genai

# =========================
# 환경 변수
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

KEYWORDS = [
    'metasurface AND "noise-like pulse"',
    'metasurface AND "saturable absorber"',
    'laser AND "two-temperature model"'
]

# =========================
# Gemini 요약
# =========================
def ask_gemini(prompt_text):
    try:
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"❌ Gemini 오류: {str(e)}"


# =========================
# arXiv 검색
# =========================
def get_arxiv_papers(query):
    encoded_query = requests.utils.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending'

    try:
        res = requests.get(url, timeout=30)
        root = ET.fromstring(res.text)

        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        papers = []

        for e in entries:
            papers.append({
                "title": e.find('{http://www.w3.org/2005/Atom}title').text.strip(),
                "date": e.find('{http://www.w3.org/2005/Atom}published').text[:10],
                "abstract": e.find('{http://www.w3.org/2005/Atom}summary').text.strip()
            })

        return papers
    except:
        return []


# =========================
# Semantic Scholar 검색
# =========================
def get_semantic_papers(query):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": 3,
        "fields": "title,abstract,year"
    }

    try:
        res = requests.get(url, params=params, timeout=30)
        data = res.json()

        papers = []
        for p in data.get("data", []):
            if not p.get("abstract"):
                continue

            papers.append({
                "title": p["title"],
                "date": str(p.get("year", "")),
                "abstract": p["abstract"]
            })

        return papers
    except:
        return []


# =========================
# Discord 전송 (비동기)
# =========================
async def send_discord(session, message):
    try:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print("Discord 전송 실패:", e)


# =========================
# 메인 실행
# =========================
async def main():
    async with aiohttp.ClientSession() as session:

        await send_discord(session, "📡 **논문 분석 엔진 시작 (v2 안정화 버전)**")

        for kw in KEYWORDS:
            try:
                arxiv = get_arxiv_papers(kw)
                semantic = get_semantic_papers(kw)

                papers = arxiv + semantic

                if not papers:
                    await send_discord(session, f"ℹ️ **[{kw}]**: 신규 논문 없음")
                    continue

                # 중복 제거 (title 기준)
                seen = set()
                unique_papers = []
                for p in papers:
                    if p["title"] not in seen:
                        seen.add(p["title"])
                        unique_papers.append(p)

                paper_text = ""
                for p in unique_papers[:5]:
                    paper_text += f"제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract']}\n\n"

                prompt = f"""
너는 광학 및 레이저 물리 연구자이다.

다음 논문들을:
1. 핵심 물리 메커니즘 중심으로
2. 실험/이론 구분해서
3. 연구 가치 기준으로

간결하지만 전문적으로 한국어로 요약해라.

{paper_text}
"""

                summary = ask_gemini(prompt)

                await send_discord(
                    session,
                    f"## 📌 분야: {kw}\n\n{summary}"
                )

                await asyncio.sleep(3)

            except Exception as e:
                await send_discord(
                    session,
                    f"❌ **[{kw}] 오류:** {str(e)}"
                )

        await send_discord(session, "🏁 **리포트 완료**")


# =========================
# 실행
# =========================
if __name__ == "__main__":
    asyncio.run(main())
