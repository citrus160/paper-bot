import os
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
import time

# 1. 환경 변수 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 2. 검색 키워드 리스트 (원하는 만큼 추가/수정하세요)
KEYWORDS = [
    'metasurface AND "noise-like pulse"',
    'metasurface AND "saturable absorber"',
    '"two-temperature model" AND laser'
]

def get_papers_arxiv(query):
    """arXiv에서 최신 논문을 검색합니다."""
    print(f"🔍 검색 중: {query}")
    encoded_query = requests.utils.quote(query)
    # 최근 논문 상위 3개 검색
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending'
    
    try:
        response = requests.get(url, timeout=15)
        root = ET.fromstring(response.text)
        papers = []
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
            summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
            papers.append(f"Title: {title}\nAbstract: {summary[:500]}...")
        return papers
    except Exception as e:
        print(f"❌ 검색 오류: {e}")
        return []

def main():
    # Gemini 설정
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    for kw in KEYWORDS:
        results = get_papers_arxiv(kw)
        
        # [핵심] 논문이 없는 경우 처리
        if not results:
            print(f"⚠️ '{kw}' 결과 없음")
            no_paper_msg = f"ℹ️ **분야: {kw}**\n이번 주에는 이 키워드에 대한 새로운 추천 논문이 없습니다."
            requests.post(DISCORD_WEBHOOK_URL, json={"content": no_paper_msg})
            continue

        # 논문이 있는 경우 요약 진행
        print(f"🤖 '{kw}' 요약 중...")
        paper_context = "\n\n".join(results)
        prompt = f"""
        당신은 광학/광자학 전문 연구원입니다. 
        키워드 [{kw}]로 검색된 다음 최신 논문들을 한국어로 전문성 있게 요약해 주세요.
        
        형식:
        ## 📌 분야: {kw}
        * **논문 제목**
        * **핵심 요약**: (연구 목적과 결과를 한 줄로)
        * **기술적 포인트**: (구체적인 물리적 현상이나 수치 등 언급)
        ---
        
        논문 목록:
        {paper_context}
        """
        
        try:
            response = model.generate_content(prompt)
            requests.post(DISCORD_WEBHOOK_URL, json={"content": response.text})
            print(f"✅ '{kw}' 전송 완료")
            time.sleep(2) # 전송 간격 조절
        except Exception as e:
            print(f"❌ Gemini 에러: {e}")

if __name__ == "__main__":
    main()
