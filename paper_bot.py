import os
import requests
import xml.etree.ElementTree as ET
import asyncio
import aiohttp
import json
from datetime import datetime

# 환경 변수
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 관심 주제
TOPICS = ["Metasurface AND (saturable absorber OR fiber laser)", 
          "Metalens AND (Terahertz OR THz)"]

def ask_groq(prompt_text, system_prompt=None):
    """Groq API 호출"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt_text})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.3
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res_data = res.json()
        if "error" in res_data:
            return f"❌ Groq 에러: {res_data['error'].get('message', 'Unknown')}"
        return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ 통신 오류: {str(e)}"

def get_arxiv_papers(query, max_results=5):
    """arxiv에서 논문 가져오기"""
    encoded_query = requests.utils.quote(query)
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query={encoded_query}"
        f"&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        res = requests.get(url, timeout=30)
        root = ET.fromstring(res.text)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        papers = []
        for e in entries:
            papers.append({
                "title": e.find("{http://www.w3.org/2005/Atom}title").text.strip(),
                "date": e.find("{http://www.w3.org/2005/Atom}published").text[:10],
                "abstract": e.find("{http://www.w3.org/2005/Atom}summary").text.strip(),
                "link": e.find("{http://www.w3.org/2005/Atom}id").text.strip(),
                "source": "arXiv"
            })
        return papers
    except Exception as e:
        print(f"arxiv 오류: {e}")
        return []

def get_semantic_scholar_papers(query, max_results=5):
    """Semantic Scholar에서 논문 가져오기"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,year,externalIds,publicationDate,url",
        "sort": "relevance"
    }
    try:
        res = requests.get(url, params=params, timeout=30)
        data = res.json()

        papers = []
        for p in data.get("data", []):
            if not p.get("abstract"):
                continue
            # 날짜 처리
            date = p.get("publicationDate") or f"{p.get('year', 'N/A')}-01-01"
            # 링크 처리
            arxiv_id = p.get("externalIds", {}).get("ArXiv")
            link = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else p.get("url", "N/A")

            papers.append({
                "title": p.get("title", "").strip(),
                "date": date[:10],
                "abstract": p.get("abstract", "").strip(),
                "link": link,
                "source": "Semantic Scholar"
            })
        return papers
    except Exception as e:
        print(f"Semantic Scholar 오류: {e}")
        return []

def merge_and_deduplicate(papers_list):
    """여러 소스 논문 합치고 중복 제거 (제목 기준)"""
    seen_titles = set()
    merged = []
    for paper in papers_list:
        title_key = paper["title"].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            merged.append(paper)
    return merged

def select_papers(topic, papers):
    """Groq이 논문 선별 (관련성 + 최신성 기준)"""
    paper_list = "\n\n".join([
        f"[{i+1}] Title: {p['title']}\nDate: {p['date']}\nSource: {p['source']}\nAbstract: {p['abstract'][:300]}..."
        for i, p in enumerate(papers)
    ])

    prompt = f"""The following are {len(papers)} papers retrieved for the topic "{topic}".
Consider both relevance (how closely related to the topic) and recency (how recent the date is),
and select the most important papers up to 2.

Reply ONLY with a JSON array of the selected paper numbers. Example: [1, 3]
Do not say anything else, just output the JSON.

Paper list:
{paper_list}"""

    result = ask_groq(prompt)

    try:
        result = result.strip()
        indices = json.loads(result)
        selected = [papers[i - 1] for i in indices if 1 <= i <= len(papers)]
        return selected
    except Exception:
        return papers[:2]

def summarize_paper(paper):
    """논문 영어 요약"""
    prompt = f"""Summarize the key content of the following paper in 2-3 sentences in English.

Title: {paper['title']}
Date: {paper['date']}
Abstract: {paper['abstract']}"""

    return ask_groq(prompt)

async def send_discord(session, message):
    """Discord 메시지 전송"""
    try:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": message[:2000]})
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Discord 전송 오류: {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        now = datetime.now().strftime("%Y-%m-%d")
        await send_discord(session, f"# 📚 Weekly Paper Report ({now})")

        for topic in TOPICS:
            await send_discord(session, f"\n## 🔍 {topic}")

            # 1. arxiv + Semantic Scholar에서 논문 가져오기
            arxiv_papers = get_arxiv_papers(topic, max_results=5)
            ss_papers = get_semantic_scholar_papers(topic, max_results=5)

            # 2. 합치고 중복 제거
            all_papers = merge_and_deduplicate(arxiv_papers + ss_papers)

            if not all_papers:
                await send_discord(session, "ℹ️ 논문 검색 결과 없음")
                continue

            await send_discord(
                session,
                f"📋 arXiv {len(arxiv_papers)}편 + Semantic Scholar {len(ss_papers)}편 "
                f"→ 중복 제거 후 {len(all_papers)}편 → AI 선별 중..."
            )

            # 3. Groq이 선별
            selected = select_papers(topic, all_papers)
            await send_discord(session, f"✅ {len(selected)}편 선별 완료\n")

            # 4. 선별된 논문 요약
            for i, paper in enumerate(selected, 1):
                summary = summarize_paper(paper)
                message = (
                    f"**[{i}] {paper['title']}**\n"
                    f"📅 {paper['date']} | 📌 {paper['source']}\n"
                    f"{summary}\n"
                    f"🔗 {paper['link']}"
                )
                await send_discord(session, message)
                await asyncio.sleep(3)

        await send_discord(session, "\n🏁 Done!")

if __name__ == "__main__":
    asyncio.run(main())
