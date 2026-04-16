import os
import datetime
import requests
from scholarly import scholarly
import google.generativeai as genai

# 1. 설정 (GitHub Secrets에 저장할 변수들)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID")

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 논문 검색 키워드
KEYWORDS = 'metasurface "saturable absorber"
def get_papers():
    search_query = scholarly.search_pubs(KEYWORDS)
    papers = []
    # 최근 논문 5개만 추출
    for i, paper in enumerate(search_query):
        if i >= 5: break
        papers.append({
            "title": paper['bib']['title'],
            "pub_url": paper.get('pub_url', 'No Link'),
            "abstract": paper['bib'].get('abstract', 'No Abstract'),
            "author": paper['bib'].get('author', ['Unknown'])
        })
    return papers

def summarize_with_gemini(paper_list):
    prompt = f"너는 광학 연구원이야. 다음 논문 리스트를 읽고, 질문자의 연구(메타표현체 기반 포화흡수체, 1um 펄스 레이저)와 관련성이 높은 순서대로 요약해줘. 한국어로 작성해줘.\n\n{paper_list}"
    response = model.generate_content(prompt)
    return response.text

def send_to_discord(content):
    data = {"content": f"📅 **이번 주 최신 논문 브리핑**\n\n{content}"}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

# 메인 로직
if __name__ == "__main__":
    paper_data = get_papers()
    summary = summarize_with_gemini(paper_data)
    send_to_discord(summary)
