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
          "Metalens AND (THz)"]

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

def get_arxiv_papers(query, max_results=10):
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
                "link": e.find("{http://www.w3.org/2005/Atom}id").text.strip()
            })
        return papers
    except Exception as e:
        print(f"arxiv 오류: {e}")
        return []

def select_papers(topic, papers):
    """Groq이 논문 선별 (관련성 + 최신성 기준)"""
    paper_list = "\n\n".join([
        f"[{i+1}] 제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract'][:300]}..."
        for i, p in enumerate(papers)
    ])

    prompt = f"""다음은 "{topic}" 키워드로 검색된 논문 {len(papers)}편입니다.
관련성(키워드와 얼마나 밀접한가)과 최신성(날짜가 최근인가)을 모두 고려하여
가장 중요한 논문 최대 5편을 선별해주세요.

선별한 논문의 번호만 JSON 배열로 답해주세요. 예시: [1, 3, 5]
다른 말은 하지 말고 JSON만 출력하세요.

논문 목록:
{paper_list}"""

    result = ask_groq(prompt)

    try:
        # JSON 파싱
        result = result.strip()
        indices = json.loads(result)
        selected = [papers[i - 1] for i in indices if 1 <= i <= len(papers)]
        return selected
    except Exception:
        # 파싱 실패시 상위 3개 반환
        return papers[:3]

def summarize_paper(paper):
    """논문 한국어 요약"""
    prompt = f"""다음 논문을 한국어로 요약해주세요.

제목: {paper['title']}
날짜: {paper['date']}
초록: {paper['abstract']}

아래 형식으로 작성해주세요:
• 핵심 내용: (2~3문장)
• 주요 기여: (1~2문장)"""

    return ask_groq(prompt)

async def send_discord(session, message):
    """Discord 메시지 전송"""
    try:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": message[:2000]})
        await asyncio.sleep(1)  # 속도 제한 방지
    except Exception as e:
        print(f"Discord 전송 오류: {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        now = datetime.now().strftime("%Y-%m-%d")
        await send_discord(session, f"# 📚 주간 논문 리포트 ({now})")

        for topic in TOPICS:
            await send_discord(session, f"\n## 🔍 {topic}")

            # 1. arxiv에서 논문 10개 가져오기
            papers = get_arxiv_papers(topic, max_results=10)
            if not papers:
                await send_discord(session, "ℹ️ 논문 검색 결과 없음")
                continue

            # 2. Groq이 관련성+최신성 기준으로 선별
            await send_discord(session, f"📋 {len(papers)}편 검색 → AI 선별 중...")
            selected = select_papers(topic, papers)
            await send_discord(session, f"✅ {len(selected)}편 선별 완료\n")

            # 3. 선별된 논문 요약
            for i, paper in enumerate(selected, 1):
                summary = summarize_paper(paper)
                message = (
                    f"**[{i}] {paper['title']}**\n"
                    f"📅 {paper['date']}\n"
                    f"{summary}\n"
                    f"🔗 {paper['link']}"
                )
                await send_discord(session, message)
                await asyncio.sleep(3)  # Groq 속도 제한 방지

        await send_discord(session, "\n🏁 이번 주 리포트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
