import os
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
import time

# 1. 환경 변수 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 2. 검색 키워드 리스트
KEYWORDS = [
    'metasurface AND "noise-like pulse"',
    'metasurface AND "saturable absorber"',
    '"two-temperature model" AND laser'
]

def get_papers_arxiv(query):
    """arXiv에서 논문을 검색하고 기본 정보를 리스트로 반환합니다."""
    encoded_query = requests.utils.quote(query)
    # 최신 논문 상위 3개 호출
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending'
    
    try:
        response = requests.get(url, timeout=15)
        root = ET.fromstring(response.text)
        papers = []
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' ')
            published = entry.find('{http://www.w3.org/2005/Atom}published').text.strip()[:10] # 날짜만 추출 (YYYY-MM-DD)
            summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip().replace('\n', ' ')
            
            papers.append({
                "title": title,
                "date": published,
                "abstract": summary
            })
        return papers
    except Exception as e:
        print(f"❌ 검색 오류 ({query}): {e}")
        return []

def main():
    # Gemini 설정
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    for kw in KEYWORDS:
        raw_papers = get_papers_arxiv(kw)
        
        if not raw_papers:
            msg = f"ℹ️ **분야: {kw}**\n이번 주에는 새로운 추천 논문이 없습니다."
            requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
            continue

        # 제미나이에게 논문 정리를 시킵니다.
        print(f"🤖 제미나이가 '{kw}' 논문을 정리 중입니다...")
        
        # 데이터를 텍스트로 변환하여 제미나이에게 전달
        paper_input = ""
        for p in raw_papers:
            paper_input += f"제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract']}\n\n"

        prompt = f"""
        당신은 광학 분야 전문 AI 비서입니다. 아래 제공된 논문 정보를 바탕으로 연구자를 위한 브리핑을 작성해주세요.
        
        **요청 사항**:
        1. 각 논문마다 아래의 형식을 반드시 지켜주세요.
        2. 초록은 핵심만 간결하게 한국어로 번역 및 요약해주세요.
        3. 키워드 [{kw}]에 대한 보고서임을 명시하세요.

        **출력 형식**:
        ## 📂 분야: {kw}
        ---
        ### 📄 논문 제목: [여기에 제목]
        * 📅 **업로드 날짜**: [YYYY-MM-DD]
        * 📝 **초록 요약**: [한국어로 요약된 내용]
        
        (다음 논문이 있다면 위 형식을 반복)
        """
        
        try:
            # 제미나이가 직접 검색 결과를 가공
            combined_prompt = prompt + "\n\n[논문 데이터]\n" + paper_input
            response = model.generate_content(combined_prompt)
            
            # 디스코드 전송
            requests.post(DISCORD_WEBHOOK_URL, json={"content": response.text})
            print(f"✅ '{kw}' 분야 전송 완료")
            time.sleep(3) # 전송 간격 유지
            
        except Exception as e:
            print(f"❌ 제미나이 처리 오류: {e}")

if __name__ == "__main__":
    main()
