import os
import requests
from scholarly import scholarly
import google.generativeai as genai

# 환경 변수 가져오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def get_papers():
    print("논문 검색 시작...")
    try:
        # 검색어를 조금 더 단순하게 바꿔서 차단 확률을 낮춥니다.
        search_query = scholarly.search_pubs('metasurface "saturable absorber"')
        papers = []
        for i, paper in enumerate(search_query):
            if i >= 3: break # 일단 3개만 테스트
            papers.append(f"Title: {paper['bib']['title']}\nAbstract: {paper['bib'].get('abstract', 'No abstract')[:300]}...")
        
        if not papers:
            print("검색 결과가 없습니다.")
        return "\n\n".join(papers)
    except Exception as e:
        print(f"구글 스칼라 검색 중 에러 발생: {e}")
        return None

def main():
    if not DISCORD_WEBHOOK_URL:
        print("디스코드 웹훅 URL이 설정되지 않았습니다.")
        return

    paper_text = get_papers()
    
    if paper_text:
        print("Gemini 요약 중...")
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"다음 논문들을 연구자 관점에서 한국어로 요약해줘:\n\n{paper_text}")
        
        # 디스코드 전송
        res = requests.post(DISCORD_WEBHOOK_URL, json={"content": response.text})
        print(f"디스코드 전송 결과: {res.status_code}")
    else:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": "이번 주엔 조건에 맞는 논문을 찾지 못했습니다."})

if __name__ == "__main__":
    main()
