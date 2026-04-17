import os
import requests
import xml.etree.ElementTree as ET
import time

# 환경 변수
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 키워드 설정
KEYWORDS = [
    'metasurface AND "noise-like pulse"',
    'metasurface AND "saturable absorber"',
    'laser AND "two-temperature model"'
]

def ask_gemini(prompt_text):
    """v1 API와 정확한 모델명을 사용하여 호출합니다."""
    # [수정] v1beta 대신 v1을 사용하고 모델명을 정확히 입력합니다.
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res_json = res.json()
        
        # 에러 응답이 온 경우 로그 출력
        if 'error' in res_json:
            return f"❌ Gemini API 에러: {res_json['error'].get('message', '알 수 없는 에러')}"
            
        # 정상 답변 파싱
        if 'candidates' in res_json and len(res_json['candidates']) > 0:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        
        return "⚠️ 답변 생성 실패 (구조 문제)"
    except Exception as e:
        return f"❌ 시스템 오류: {str(e)}"

def get_papers_arxiv(query):
    """arXiv 검색"""
    encoded_query = requests.utils.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending'
    try:
        response = requests.get(url, timeout=40)
        if response.status_code != 200: return []
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
    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🛰️ **논문 분석 시스템을 최종 재가동합니다.**"})

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
            
            # 메시지 전송
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"## 📌 분야: {kw}\n\n{summary}"})
            time.sleep(5)

        except Exception as e:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"❌ **[{kw}]** 에러 발생: {str(e)}"})

    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🏁 **리포트 종료**"})

if __name__ == "__main__":
    main()
