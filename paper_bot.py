import os
import requests
import xml.etree.ElementTree as ET
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta

# 환경 변수
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 관심 주제
TOPICS = ["Metasurface", "Laser physics"]

def ask_gemini_strict(prompt_text):
    """구글 v1 정식 API 규격에 맞춘 호출 방식입니다."""
    # [수정] 결제 유저에게 가장 확실한 v1 정식 엔드포인트
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    # [수정] 구글이 요구하는 표준 페이로드 구조
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res_data = res.json()
        
        # 1. 서버가 에러를 보낸 경우 (이게 핵심 단서입니다!)
        if 'error' in res_data:
            code = res_data['error'].get('code', 'Unknown')
            msg = res_data['error'].get('message', 'No message')
            return f"❌ 구글 서버 응답 에러({code}): {msg}"
        
        # 2. 정상 응답인 경우
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            return res_data['candidates'][0]['content']['parts'][0]['text']
        
        return f"⚠️ 알 수 없는 응답 구조: {str(res_data)[:100]}"
    except Exception as e:
        return f"❌ 통신 오류: {str(e)}"

def get_arxiv_papers(query):
    encoded_query = requests.utils.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&max_results=3&sortBy=submittedDate&sortOrder=descending'
    try:
        res = requests.get(url, timeout=30)
        root = ET.fromstring(res.text)
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        
        one_month_ago = datetime.now() - timedelta(days=30)
        papers = []
        for e in entries:
            pub_date_str = e.find('{http://www.w3.org/2005/Atom}published').text[:10]
            papers.append({
                "title": e.find('{http://www.w3.org/2005/Atom}title').text.strip(),
                "date": pub_date_str,
                "abstract": e.find('{http://www.w3.org/2005/Atom}summary').text.strip()
            })
        return papers
    except:
        return []

async def send_discord(session, message):
    await session.post(DISCORD_WEBHOOK_URL, json={"content": message[:2000]})

async def main():
    async with aiohttp.ClientSession() as session:
        await send_discord(session, "🛠️ **결제 계정 전용 정밀 진단 모드 가동**")

        for topic in TOPICS:
            await send_discord(session, f"🔍 주제: {topic}")
            raw_papers = get_arxiv_papers(topic)

            if not raw_papers:
                await send_discord(session, "ℹ️ 최근 논문 검색 결과 없음")
                continue

            # 분석 요청
            paper_info = f"제목: {raw_papers[0]['title']}\n초록: {raw_papers[0]['abstract']}"
            prompt = f"다음 논문을 한국어로 요약해줘:\n\n{paper_info}"
            
            result = ask_gemini_strict(prompt)
            await send_discord(session, f"## 📌 결과 리포트\n{result}")
            await asyncio.sleep(5)

        await send_discord(session, "🏁 진단 종료")

if __name__ == "__main__":
    asyncio.run(main())
