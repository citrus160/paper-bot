import os
import requests
import xml.etree.ElementTree as ET
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# v1 정식 버전 설정
genai.configure(api_key=GEMINI_API_KEY, transport='rest')

TOPICS = [
    "Metasurface Saturable Absorber",
    "Terahertz metalens",
    "Nonlinear optics with nanophotonic structures"
]

def ask_gemini(prompt_text):
    try:
        # Tier 유저라면 Pro를 우선 시도하되 실패 시 Flash로 자동 전환
        for model_name in ["gemini-1.5-pro", "gemini-1.5-flash"]:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt_text)
                if response and response.text:
                    return response.text
            except:
                continue
    except:
        return None

def get_arxiv_papers(query):
    """검색 범위를 유연하게 조정하여 논문을 가져옵니다."""
    encoded_query = requests.utils.quote(query)
    # 날짜 필터를 쿼리문 안에서 빼고, 대신 정렬 순서를 최신순으로 하여 10개까지 가져옵니다.
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending'
    
    try:
        res = requests.get(url, timeout=30)
        root = ET.fromstring(res.text)
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        
        one_month_ago = datetime.now() - timedelta(days=30)
        papers = []
        
        for e in entries:
            pub_date_str = e.find('{http://www.w3.org/2005/Atom}published').text[:10]
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
            
            # 검색 결과 중 최근 1개월 이내 것만 리스트에 담음
            if pub_date >= one_month_ago:
                papers.append({
                    "title": e.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' '),
                    "date": pub_date_str,
                    "journal": "arXiv (Preprint)",
                    "abstract": e.find('{http://www.w3.org/2005/Atom}summary').text.strip().replace('\n', ' ')
                })
        return papers
    except:
        return []

async def send_discord(session, message):
    if not message: return
    for i in range(0, len(message), 2000):
        await session.post(DISCORD_WEBHOOK_URL, json={"content": message[i:i+2000]})

async def main():
    async with aiohttp.ClientSession() as session:
        await send_discord(session, "📡 **논문 탐색 엔진 가동 (검색 범위 최적화 버전)**")

        for topic in TOPICS:
            # Step 1: 검색어 생성 (너무 복잡하지 않게 유도)
            query_prompt = f"연구 주제 [{topic}]를 arXiv에서 검색하기 위한 2~3개의 핵심 키워드 조합만 영어로 보내줘. 예: (Metasurface AND Laser). 다른 설명 금지."
            optimized_query = ask_gemini(query_prompt)
            if not optimized_query: continue
            optimized_query = optimized_query.strip().replace('"', '')

            # Step 2: 논문 수집
            raw_papers = get_arxiv_papers(optimized_query)

            if not raw_papers:
                await send_discord(session, f"ℹ️ **[{topic}]**: 최근 1개월 내 arXiv에 등록된 관련 논문이 없습니다.")
                continue

            # Step 3: 제미나이의 정밀 선별
            papers_info = "\n\n".join([f"제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract']}" for p in raw_papers])
            
            analysis_prompt = f"""
너는 광학 전문가다. 아래 논문 리스트에서 주제 [{topic}]과 밀접한 관련이 있는 논문만 골라라.
최근 1개월 내 논문들이다.

[작성 형식]
- **제목**: (원문 제목)
- **출간 날짜**: (날짜)
- **저널**: arXiv (Preprint)
- **초록 요약**: (한국어 3줄 요약)
- **전문가 평가**: (연구 가치 1줄)

만약 주제와 맞는 논문이 하나도 없다면 "해당 주제와 일치하는 최신 논문이 없습니다."라고 답변해라.

논문 데이터:
{papers_info}
"""
            report = ask_gemini(analysis_prompt)
            await send_discord(session, f"## 📡 주제: {topic}\n{report}")
            await asyncio.sleep(8)

        await send_discord(session, "🏁 **탐색 종료**")

if __name__ == "__main__":
    asyncio.run(main())
