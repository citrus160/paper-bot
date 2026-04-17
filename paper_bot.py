
import os
import requests
import xml.etree.ElementTree as ET
import time

# 환경 변수
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

KEYWORDS = [
    'metasurface AND "noise-like pulse"',
    'metasurface AND "saturable absorber"',
    'laser AND "two-temperature model"'
]

def get_papers_arxiv(query):
    """arXiv 검색 (타임아웃 및 예외 처리 강화)"""
    encoded_query = requests.utils.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending'
    
    try:
        # 타임아웃 40초로 대폭 연장
        response = requests.get(url, timeout=40)
        if response.status_code != 200:
            return []
            
        root = ET.fromstring(response.text)
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        
        papers = []
        for entry in entries:
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' ')
            date = entry.find('{http://www.w3.org/2005/Atom}published').text.strip()[:10]
            abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip().replace('\n', ' ')
            papers.append({"title": title, "date": date, "abstract": abstract})
        return papers
    except:
        return []

def ask_gemini(prompt_text):
    """라이브러리 버그를 피하기 위해 REST API로 직접 Gemini 호출"""
    # 모델 경로를 v1beta가 아닌 일반 v1으로 시도하여 404 에러 원천 차단
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res_json = res.json()
        # 제미나이 답변 추출
        return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"요약 생성 중 에러 발생: {str(e)}"

def main():
    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🛰️ **AI 논문 분석 시스템을 재가동합니다.**"})

    for kw in KEYWORDS:
        try:
            print(f"작업 중: {kw}")
            raw_papers = get_papers_arxiv(kw)
            
            if not raw_papers:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": f"ℹ️ **[{kw}]** 분야: 신규 논문이 없거나 검색 서버가 응답하지 않습니다."})
                continue

            # 논문 데이터 정리
            paper_input = ""
            for p in raw_papers:
                paper_input += f"제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract']}\n\n"

            prompt = f"당신은 광학 연구원입니다. 다음 논문들을 제목, 날짜, 한국어 요약(전문적) 형식으로 정리해줘:\n\n{paper_input}"
            
            # Gemini에게 물어보기
            summary = ask_gemini(prompt)
            
            # 디스코드 전송 (2000자 초과 방지)
            if len(summary) > 1900:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": summary[:1900]})
                requests.post(DISCORD_WEBHOOK_URL, json={"content": summary[1900:3800]})
            else:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": summary})
            
            print(f"완료: {kw}")
            time.sleep(5) # 디스코드 속도 제한 방지

        except Exception as e:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"❌ **[{kw}]** 처리 중 오류: {str(e)}"})
            continue

    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🏁 **모든 보고를 마쳤습니다.**"})

if __name__ == "__main__":
    main()
