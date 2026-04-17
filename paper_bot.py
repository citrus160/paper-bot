import os
import requests
import xml.etree.ElementTree as ET
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
import google.generativeai as genai

# ==========================================
# 1. 환경 변수 및 설정
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# API 버전을 v1으로 고정하고 REST 방식으로 설정 (404 에러 방지)
genai.configure(api_key=GEMINI_API_KEY, transport='rest')

# 연구 주제 리스트 (여기에 관심 있는 주제를 자유롭게 적으세요)
TOPICS = [
    "Metasurface based Saturable Absorber for ultrafast laser",
    "Two-temperature model in laser-matter interaction",
    "Nonlinear optics with nanophotonic structures"
]

# ==========================================
# 2. 핵심 기능 함수
# ==========================================

def ask_gemini(prompt_text):
    """제미나이 1.5 Pro 모델을 사용하여 판단 및 요약 수행"""
    try:
        # 결제 등급(Tier) 유저라면 Pro 모델이 더 정교한 판단을 내립니다.
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt_text)
        if response and response.text:
            return response.text
    except Exception as e:
        print(f"Gemini 호출 오류: {e}")
        return None
    return None

def get_arxiv_papers(query):
    """arXiv에서 최근 1개월 이내의 논문을 검색"""
    # 1개월 전 날짜 계산 (arXiv 검색 포맷: YYYYMMDDHHMMSS)
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d%H%M%S')
    
    encoded_query = requests.utils.quote(query)
    # 최근 1개월 내 업데이트된 논문만 타겟팅 (최대 5개 추출)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}+AND+lastUpdatedDate:[{one_month_ago}+TO+20300101000000]&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending'
    
    try:
        res = requests.get(url, timeout=30)
        root = ET.fromstring(res.text)
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        
        papers = []
        for e in entries:
            papers.append({
                "title": e.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' '),
                "date": e.find('{http://www.w3.org/2005/Atom}published').text[:10],
                "journal": "arXiv (Preprint)",
                "abstract": e.find('{http://www.w3.org/2005/Atom}summary').text.strip().replace('\n', ' ')
            })
        return papers
    except Exception as e:
        print(f"arXiv 검색 중 오류: {e}")
        return []

async def send_discord(session, message):
    """디스코드 웹훅 전송 (글자 수 제한 대응)"""
    if not message: return
    for i in range(0, len(message), 2000):
        await session.post(DISCORD_WEBHOOK_URL, json={"content": message[i:i+2000]})

# ==========================================
# 3. 메인 로직 (판단 및 선별)
# ==========================================

async def main():
    async with aiohttp.ClientSession() as session:
        await send_discord(session, "🛰️ **제미나이 지능형 논문 비서 가동 (최근 1개월 분석)**")

        for topic in TOPICS:
            # [Step 1] 제미나이에게 최적의 검색어 생성을 맡김
            query_prompt = f"연구 주제 [{topic}]에 대해 arXiv에서 최근 1개월간 발표된 논문을 찾기 위한 전문적인 영어 검색어 조합을 딱 한 줄만 만들어줘. 검색어만 보내."
            optimized_query = ask_gemini(query_prompt)
            
            if not optimized_query:
                continue
            optimized_query = optimized_query.strip().replace('"', '')
            
            # [Step 2] 논문 데이터 수집
            raw_papers = get_arxiv_papers(optimized_query)

            if not raw_papers:
                await send_discord(session, f"ℹ️ **[{topic}]**: 최근 1개월 내 검색된 논문이 없습니다.")
                continue

            # [Step 3] 제미나이가 초록을 읽고 적합성 판단 및 리포트 작성
            papers_info = "\n\n".join([f"제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract']}" for p in raw_papers])
            
            analysis_prompt = f"""
너는 광학 및 레이저 물리 분야의 전문 연구원이다.
아래 논문 리스트는 연구 주제 [{topic}]와 관련하여 최근 1개월 내에 발표된 것들이다.

[수행 지침]
1. 각 논문의 초록을 깊이 있게 읽고, 주제 [{topic}]과 학술적으로 정말 밀접한 관련이 있는지 판단해라.
2. 관련성이 낮은 논문(단순 키워드 매칭 등)은 리스트에서 제외해라.
3. 선별된 논문에 대해서만 다음 형식을 지켜 한국어로 보고해라:
   ---
   ### 📄 논문 제목: (원문 제목)
   * 📅 **출간 날짜**: (날짜)
   * 🏛️ **저널**: (arXiv 혹은 확인 가능한 저널명)
   * 📝 **초록 요약**: (핵심 물리 메커니즘을 중심으로 연구자가 이해하기 쉽게 3줄 요약)
   * 💡 **선정 이유**: (이 논문이 해당 연구 주제에서 왜 중요한지 전문적인 견해)

만약 모든 논문이 연구 주제와 적합하지 않다면, "해당 주제에 대해 최근 1개월 내 추천할 만한 적합한 논문이 없습니다."라고만 답변해라.

논문 데이터:
{papers_info}
"""
            report = ask_gemini(analysis_prompt)
            
            if report:
                await send_discord(session, f"## 📡 주제 분석: {topic}\n{report}")
            
            # API 할당량 및 디스코드 속도 제한을 위해 대기
            await asyncio.sleep(10)

        await send_discord(session, "🏁 **연구 리포트 생성을 마쳤습니다.**")

if __name__ == "__main__":
    asyncio.run(main())
