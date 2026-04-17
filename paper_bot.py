import os
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
import time

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 분야별 키워드 (테스트를 위해 3개를 명확히 둠)
KEYWORDS = [
    'metasurface AND "noise-like pulse"',
    'metasurface AND "saturable absorber"',
    '"two-temperature model" AND laser'
]

def main():
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    # 시작 알림 (이게 안 오면 웹훅 URL 문제)
    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🤖 **논문 봇 가동 시작! 총 3개의 분야를 탐색합니다.**"})

    for i, kw in enumerate(KEYWORDS):
        try:
            # 1. 진행 상황 알림
            print(f">>> [{i+1}/{len(KEYWORDS)}] {kw} 작업 시작")
            
            # 2. arXiv 검색
            encoded_query = requests.utils.quote(kw)
            url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending'
            response = requests.get(url, timeout=15)
            root = ET.fromstring(response.text)
            
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            
            # 3. 논문이 없는 경우
            if not entries:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": f"ℹ️ **[{kw}]** 분야는 이번 주 신규 논문이 없습니다."})
                continue

            # 4. 논문이 있는 경우 (제미나이 요약)
            paper_data = ""
            for entry in entries:
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' ')
                date = entry.find('{http://www.w3.org/2005/Atom}published').text.strip()[:10]
                abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip().replace('\n', ' ')
                paper_data += f"제목: {title}\n날짜: {date}\n초록: {abstract}\n\n"

            prompt = f"키워드 [{kw}]의 논문들을 제목, 날짜, 한국어 초록 요약(전문성 있게) 형식으로 정리해줘:\n\n{paper_data}"
            ai_response = model.generate_content(prompt)

            # 5. 전송
            # 메시지가 너무 길면 잘라서 전송 (디스코드 2000자 제한 방지)
            final_text = ai_response.text
            if len(final_text) > 1900:
                parts = [final_text[i:i+1900] for i in range(0, len(final_text), 1900)]
                for p in parts:
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": p})
            else:
                requests.post(DISCORD_WEBHOOK_URL, json={"content": final_text})
            
            print(f">>> {kw} 완료")
            time.sleep(5) # 디스코드 속도 제한 방지용 (매우 중요)

        except Exception as e:
            # 에러 발생 시 디스코드에 비명 지르기
            error_msg = f"❌ **[{kw}]** 처리 중 에러 발생: {str(e)}"
            requests.post(DISCORD_WEBHOOK_URL, json={"content": error_msg})
            continue

    requests.post(DISCORD_WEBHOOK_URL, json={"content": "🏁 **모든 분야 탐색을 마쳤습니다.**"})

if __name__ == "__main__":
    main()
