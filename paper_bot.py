import os
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
import time

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

KEYWORDS = [
    'metasurface AND "noise-like pulse"',
    'metasurface AND "saturable absorber"',
    'laser AND "two-temperature model"'
]

def get_papers_arxiv(query):
    encoded_query = requests.utils.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending'
    
    # 서버 대기 시간을 늘리고, 재시도 로직 추가
    for attempt in range(2): 
        try:
            print(f"🔍 {query} 검색 중... (시도 {attempt+1})")
            response = requests.get(url, timeout=30) # 30초로 연장
            root = ET.fromstring(response.text)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            
            papers = []
            for entry in entries:
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' ')
                date = entry.find('{http://www.w3.org/2005/Atom}published').text.strip()[:10]
                abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip().replace('\n', ' ')
                papers.append({"title": title, "date": date, "abstract": abstract})
            return papers
        except Exception as e:
            print(f"⚠️ 검색 시도 중 대기 시간 초과 혹은 에러: {e}")
            time.sleep(5) # 잠시 쉬었다 재시도
    return []

def main():
    # 모델 설정을 더 안정적인 방식으로 변경
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 모델명을 가장 범용적인 'gemini-1.5-flash'로 수정
    model = genai.GenerativeModel('gemini-1.5-flash')

    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🚀 **논문 분석을 시작합니다.**"})

    for kw in KEYWORDS:
        try:
            raw_papers = get_papers_arxiv(kw)
            
            if not raw_papers:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": f"ℹ️ **[{kw}]**: 이번 주 신규 논문이 없거나 서버 응답이 없습니다."})
                continue

            paper_input = ""
            for p in raw_papers:
                paper_input += f"제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract']}\n\n"

            # 프롬프트 전달
            prompt = f"광학 연구자를 위해 키워드 [{kw}] 논문들을 제목, 날짜, 한국어 요약 형식으로 정리해줘:\n\n{paper_input}"
            
            # 요약 생성
            response = model.generate_content(prompt)
            
            # 디스코드 전송 (2000자 초과 방지)
            msg = response.text
            if len(msg) > 1900:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": msg[:1900]})
                requests.post(DISCORD_WEBHOOK_URL, json={"content": msg[1900:3800]})
            else:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
            
            print(f"✅ {kw} 전송 완료")
            time.sleep(5) 

        except Exception as e:
            # 에러 발생 시 구체적인 내용 보고
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"❌ **[{kw}]** 처리 중 오류 발생: {str(e)}"})
            continue

    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🏁 **모든 분야 리포트 완료!**"})

if __name__ == "__main__":
    main()
