import os
import requests
import xml.etree.ElementTree as ET
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
import google.generativeai as genai

# 환경 변수
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# API 설정 (강력한 설정 적용)
genai.configure(api_key=GEMINI_API_KEY, transport='rest')

# 테스트를 위해 주제를 아주 단순하게 1개만 넣어보세요.
TOPICS = ["Metasurface"] 

def ask_gemini(prompt_text):
    """실패 시 에러 내용을 직접 반환하도록 수정"""
    try:
        # 모델명을 바꿔가며 2번 시도
        for model_name in ["gemini-1.5-flash", "gemini-1.5-pro"]:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt_text)
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"{model_name} 시도 실패: {e}")
                continue
        return f"ERROR: 모든 모델 호출 실패"
    except Exception as e:
        return f"ERROR: {str(e)}"

def get_arxiv_papers(query):
    encoded_query = requests.utils.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending'
    try:
        res = requests.get(url, timeout=30)
        root = ET.fromstring(res.text)
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        
        one_month_ago = datetime.now() - timedelta(days=30)
        papers = []
        for e in entries:
            pub_date_str = e.find('{http://www.w3.org/2005/Atom}published').text[:10]
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
            if pub_date >= one_month_ago:
                papers.append({
                    "title": e.find('{http://www.w3.org/2005/Atom}title').text.strip(),
                    "date": pub_date_str,
                    "abstract": e.find('{http://www.w3.org/2005/Atom}summary').text.strip()
                })
        return papers
    except Exception as e:
        return []

async def send_discord(session, message):
    if not message: return
    await session.post(DISCORD_WEBHOOK_URL, json={"content": message})

async def main():
    async with aiohttp.ClientSession() as session:
        await send_discord(session, "📡 **진단 모드 가동: 루프 진입 시도...**")

        if not TOPICS:
            await send_discord(session, "❌ 오류: TOPICS 리스트가 비어있습니다.")
            return

        for topic in TOPICS:
            await send_discord(session, f"🔍 1단계: [{topic}] 검색어 생성 중...")
            
            # 검색어 생성 시도
            optimized_query = ask_gemini(f"Research topic: {topic}. Give me 2-3 arXiv search keywords. Only keywords.")
            
            if "ERROR" in optimized_query:
                await send_discord(session, f"❌ 제미나이 단계에서 실패: {optimized_query}")
                continue

            optimized_query = optimized_query.strip().replace('"', '')
            await send_discord(session, f"✅ 2단계: 생성된 검색어 `{optimized_query}`로 arXiv 조회 중...")

            # 논문 수집
            raw_papers = get_arxiv_papers(optimized_query)

            if not raw_papers:
                await send_discord(session, f"ℹ️ 3단계: `{optimized_query}` 관련 최신 논문 없음.")
                continue

            await send_discord(session, f"📝 4단계: 논문 {len(raw_papers)}건 발견! 요약 중...")
            
            # 요약 시도
            papers_info = "\n".join([p['title'] for p in raw_papers])
            report = ask_gemini(f"Summarize these paper titles in Korean: {papers_info}")
            
            await send_discord(session, f"## 📌 결과\n{report}")
            await asyncio.sleep(5)

        await send_discord(session, "🏁 **탐색 종료**")

if __name__ == "__main__":
    asyncio.run(main())
