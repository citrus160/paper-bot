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
        # 검색 결과가 너무 많으면 오류가 날 수 있어 키워드를 정교하게 조정했습니다.
        search_query = scholarly.search_pubs('metasurface "noise-like pulse"')
        papers = []
        for i, paper in enumerate(search_query):
            if i >= 3: break 
            title = paper['bib'].get('title', 'No Title')
            abstract = paper['bib'].get('abstract', 'No abstract available')
            papers.append(f"Title: {title}\nAbstract: {abstract[:500]}...")
        
        return "\n\n".join(papers) if papers else None
    except Exception as e:
        print(f"검색 중 에러: {e}")
        return None

def main():
    paper_text = get_papers()
    
    if paper_text:
        print("Gemini 요약 중...")
        genai.configure(api_key=GEMINI_API_KEY)
        
        # [수정 포인트] 모델명을 최신 버전인 'gemini-1.5-flash-latest'로 명시합니다.
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        try:
            response = model.generate_content(
                f"당신은 광학/광자학 전문가입니다. 다음 논문들을 핵심 위주로 한국어로 요약해줘:\n\n{paper_text}",
                generation_config=genai.types.GenerationConfig(temperature=0.3)
            )
            
            # 디바이스 전송
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🚀 **이번 주 최신 논문 요약**\n\n{response.text}"})
            print("성공적으로 전송되었습니다!")
            
        except Exception as e:
            print(f"Gemini 생성 에러: {e}")
    else:
        print("요약할 논문을 찾지 못했습니다.")

if __name__ == "__main__":
    main()
