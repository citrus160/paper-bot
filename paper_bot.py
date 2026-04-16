import os
import requests
from scholarly import scholarly
import google.generativeai as genai
import time

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def get_papers():
    print("논문 검색 시도 중...")
    try:
        # 검색 범위를 최근 1년으로 좁히고, 검색어를 더 명확히 해서 속도를 높입니다.
        search_query = scholarly.search_pubs('metasurface "noise-like pulse"', year_low=2025)
        papers = []
        
        # 딱 2개만 빠르게 가져오기
        for i, paper in enumerate(search_query):
            if i >= 2: break
            title = paper['bib'].get('title', '제목 없음')
            abstract = paper['bib'].get('abstract', '초록 없음')
            papers.append(f"Title: {title}\nAbstract: {abstract[:400]}")
            print(f"{i+1}번째 논문 발견!")
            time.sleep(1) # 구글의 의심을 피하기 위한 짧은 휴식
            
        return "\n\n".join(papers) if papers else None
    except Exception as e:
        print(f"검색 중 오류 발생 (아마 구글 차단): {e}")
        return None

def main():
    paper_text = get_papers()
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    if paper_text:
        print("Gemini 요약 중...")
        try:
            response = model.generate_content(f"광학 연구자를 위해 다음 논문을 요약해줘:\n\n{paper_text}")
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"✅ **최신 논문 도착**\n\n{response.text}"})
            print("디스코드 전송 완료!")
        except Exception as e:
            print(f"Gemini 에러: {e}")
    else:
        # 검색이 막혔을 경우를 대비해 알림을 보냅니다.
        requests.post(DISCORD_WEBHOOK_URL, json={"content": "⚠️ 구글 스칼라 검색이 일시적으로 제한되었습니다. 나중에 다시 시도하거나 검색 키워드를 조정해 보세요."})
        print("검색 결과 없음 알림 전송")

if __name__ == "__main__":
    main()
