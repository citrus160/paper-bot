import os
import requests
import google.generativeai as genai

# 환경 변수
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def get_papers_arxiv():
    print("arXiv에서 논문 검색 중 (이 방식이 훨씬 빠르고 안전합니다)...")
    # 검색어: metasurface AND "noise-like pulse"
    # 속도를 위해 최근 논문 3개만 가져옵니다.
    query = 'all:metasurface AND all:"noise-like pulse"'
    url = f'http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending'
    
    try:
        response = requests.get(url, timeout=15)
        content = response.text
        
        # 간단한 텍스트 파싱 (라이브러리 추가 설치 방지)
        papers = []
        import xml.etree.ElementTree as ET
        root = ET.fromstring(content)
        
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
            summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
            papers.append(f"Title: {title}\nAbstract: {summary[:500]}...")
            
        return "\n\n".join(papers) if papers else None
    except Exception as e:
        print(f"arXiv 검색 중 에러: {e}")
        return None

def main():
    paper_text = get_papers_arxiv()
    
    if not paper_text:
        print("논문을 찾지 못했거나 검색에 실패했습니다.")
        requests.post(DISCORD_WEBHOOK_URL, json={"content": "⚠️ 이번 주에는 새로운 논문을 찾지 못했습니다."})
        return

    print("Gemini 요약 중...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    try:
        response = model.generate_content(f"연구자를 위해 다음 광학 논문들을 한국어로 핵심 요약해줘:\n\n{paper_text}")
        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🚀 **arXiv 최신 논문 요약**\n\n{response.text}"})
        print("전송 성공!")
    except Exception as e:
        print(f"Gemini 에러: {e}")

if __name__ == "__main__":
    main()
