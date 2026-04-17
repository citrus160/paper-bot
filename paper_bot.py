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

def ask_gemini(prompt_text):
    """모델명을 풀 네임으로 수정하여 v1beta1 주소로 재시도합니다."""
    # [수정] 모델 경로를 가장 확실한 'v1beta'와 'models/gemini-1.5-flash' 조합으로 복구하되, 
    # API 호출 구조를 가장 원시적인 형태로 유지합니다.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res_json = res.json()
        
        # 에러 발생 시 상세 정보 출력
        if 'error' in res_json:
            error_code = res_json['error'].get('code')
            error_msg = res_json['error'].get('message')
            return f"❌ API 에러({error_code}): {error_msg}"
            
        if 'candidates' in res_json and len(res_json['candidates']) > 0:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        
        return "⚠️ 응답 데이터 구조에 답변이 포함되어 있지 않습니다."
    except Exception as e:
        return f"❌ 시스템 오류: {str(e)}"

def get_papers_arxiv(query):
    encoded_query = requests.utils.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending'
    try:
        response = requests.get(url, timeout=40)
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

def main():
    requests.post(DISCORD_WEBHOOK_URL, json={"content": "📡 **논문 분석 엔진을 재기동합니다. (v1beta 모델 경로 적용)**"})

    for kw in KEYWORDS:
        try:
            raw_papers = get_papers_arxiv(kw)
            if not raw_papers:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": f"ℹ️ **[{kw}]**: 신규 논문 없음"})
                continue

            paper_input = ""
            for p in raw_papers:
                paper_input += f"제목: {p['title']}\n날짜: {p['date']}\n초록: {p['abstract']}\n\n"

            prompt = f"광학 연구원을 위해 다음 논문들을 한국어로 전문성 있게 요약해줘:\n\n{paper_input}"
            summary = ask_gemini(prompt)
            
            # 결과 전송
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"## 📌 분야: {kw}\n\n{summary}"})
            time.sleep(5)

        except Exception as e:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"❌ **[{kw}]** 치명적 에러: {str(e)}"})

    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🏁 **리포트 완료**"})

if __name__ == "__main__":
    main()
