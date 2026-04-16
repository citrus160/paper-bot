import os
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
import time

# 1. 환경 변수 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 2. 검색하고 싶은 키워드 리스트 (여기에 자유롭게 추가/수정하세요)
KEYWORDS = [
    'metasurface',
    'metalens',
    'saturable absorber'
]

def get_papers_arxiv(query):
    """arXiv API를 사용하여 키워드당 최신 논문 3개를 가져옵니다."""
    print(f"🔍 검색 중: {query}")
    encoded_query = requests.utils.quote(query)
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
        print(f"❌ '{query}' 검색 중 오류: {e}")
        return []

def main():
    # Gemini 설정
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    print(f"🚀 총 {len(KEYWORDS)}개의 키워드에 대해 작업을 시작합니다.")

    for kw in KEYWORDS:
        # A. 논문 검색
        results = get_papers_arxiv(kw)
        
        if not results:
            print(f"⚠️ '{kw}'에 대한 새로운 논문이 없습니다. 건너뜁니다.")
            continue

        # B. Gemini 요약 생성
        print(f"🤖 '{kw}' 분야 요약 중...")
        paper_context = "\n\n".join(results)
        prompt = f"""
        당신은 광학/광자학 분야의 전문 연구원입니다. 
        키워드 [{kw}]로 검색된 다음 논문들을 한국어로 전문성 있게 요약해 주세요.
        
        형식:
        ## 📌 분야: {kw}
        * **논문 제목**
        * **핵심 요약**: (연구의 목적과 결과를 한 줄로)
        * **기술적 포인트**: (메타표면의 구조나 물리적 현상 등 구체적 언급)
        ---
        
        논문 목록:
        {paper_context}
        """
        
        try:
            response = model.generate_content(prompt)
            
            # C. 디스코드 전송 (키워드 하나 끝날 때마다 즉시 전송)
            message = response.text
            requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
            print(f"✅ '{kw}' 전송 완료!")
            
            # 구글 API나 디스코드 웹훅의 과부하 방지를 위해 짧게 쉽니다.
            time.sleep(2) 
            
        except Exception as e:
            print(f"❌ Gemini 에러 ({kw}): {e}")

    print("🎉 모든 작업이 완료되었습니다!")

if __name__ == "__main__":
    main()
