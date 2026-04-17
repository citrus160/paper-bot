import os
import requests
import xml.etree.ElementTree as ET
import asyncio
import aiohttp
import json
from datetime import datetime

# 환경 변수
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 이미 본 논문 저장 파일
SEEN_PAPERS_FILE = "seen_papers.json"

# 관심 주제 및 검색 쿼리 직접 지정
TOPICS = [
    {
        "name": "Metasurface Saturable Absorber",
        "queries": [
            "metasurface saturable absorber mode locking",
            "metasurface fiber laser ultrafast",
            "nonlinear metasurface passive mode locking laser"
        ]
    },
    {
        "name": "THz Metalens",
        "queries": [
            "THz metalens",
            "THz metasurface",
            "THz metalens design"
        ]
    },
    {
        "name": "Metasurface Fiber",
        "queries": [
            "metafiber",
            "metasurface integrated fiber",
            "metasurface fiber tip"
        ]
    }
]

def load_seen_papers():
    """이미 본 논문 링크 목록 불러오기"""
    if os.path.exists(SEEN_PAPERS_FILE):
        with open(SEEN_PAPERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_papers(seen_papers):
    """이미 본 논문 링크 목록 저장"""
    with open(SEEN_PAPERS_FILE, "w") as f:
        json.dump(list(seen_papers), f, indent=2)

def ask_groq(prompt_text, system_prompt=None):
    """Groq API 호출"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt_text})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.3
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        res_data = res.json()
        if "error" in res_data:
            return f"❌ Groq 에러: {res_data['error'].get('message', 'Unknown')}"
        return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ 통신 오류: {str(e)}"

def get_arxiv_papers(query, max_results=3):
    """arxiv에서 논문 가져오기"""
    encoded_query = requests.utils.quote(f'abs:"{query}"')
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query={encoded_query}"
        f"&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        res = requests.get(url, timeout=30)
        root = ET.fromstring(res.text)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        papers = []
        for e in entries:
            papers.append({
                "title": e.find("{http://www.w3.org/2005/Atom}title").text.strip(),
                "date": e.find("{http://www.w3.org/2005/Atom}published").text[:10],
                "abstract": e.find("{http://www.w3.org/2005/Atom}summary").text.strip(),
                "link": e.find("{http://www.w3.org/2005/Atom}id").text.strip(),
                "source": "arXiv"
            })
        return papers
    except Exception as e:
        print(f"arxiv 오류: {e}")
        return []

def get_openalex_papers(query, max_results=3):
    """OpenAlex에서 논문 가져오기 (초록에 키워드 포함된 것만)"""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per-page": 20,
        "sort": "publication_date:desc",
        "filter": "has_abstract:true",
        "mailto": "paper-bot@example.com"
    }
    try:
        res = requests.get(url, params=params, timeout=30)
        data = res.json()

        # 키워드 추출 (3글자 이상 단어만)
        keywords = [w.lower() for w in query.split() if len(w) > 3]

        papers = []
        for p in data.get("results", []):
            abstract = ""
            inverted = p.get("abstract_inverted_index")
            if inverted:
                words = {pos: word for word, positions in inverted.items() for pos in positions}
                abstract = " ".join(words[i] for i in sorted(words.keys()))

            if not abstract:
                continue

            # 초록에 키워드 포함된 것만 필터링
            abstract_lower = abstract.lower()
            if not any(kw in abstract_lower for kw in keywords):
                continue

            date = p.get("publication_date") or f"{p.get('publication_year', 'N/A')}-01-01"
            doi = p.get("doi", "")
            link = doi if doi else p.get("id", "N/A")

            papers.append({
                "title": p.get("title", "").strip(),
                "date": str(date)[:10],
                "abstract": abstract,
                "link": link,
                "source": "OpenAlex"
            })

            if len(papers) >= max_results:
                break

        return papers
    except Exception as e:
        print(f"OpenAlex 오류: {e}")
        return []

def merge_and_deduplicate(papers_list):
    """여러 소스 논문 합치고 중복 제거 (제목 기준)"""
    seen_titles = set()
    merged = []
    for paper in papers_list:
        title_key = paper["title"].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            merged.append(paper)
    return merged

def filter_new_papers(papers, seen_papers):
    """이미 본 논문 제외"""
    return [p for p in papers if p["link"] not in seen_papers]

def select_papers(topic_name, papers):
    """Groq이 논문 선별 (관련성 + 최신성 기준)"""
    paper_list = "\n\n".join([
        f"[{i+1}] 제목: {p['title']}\n날짜: {p['date']}\n출처: {p['source']}\n초록: {p['abstract'][:300]}..."
        for i, p in enumerate(papers)
    ])

    print(f"\n📄 {topic_name} 선별 전 논문 목록:")
    for i, p in enumerate(papers, 1):
        print(f"  [{i}] {p['title']} ({p['source']})")

    prompt = f"""당신은 광학 및 레이저 분야 논문 큐레이터입니다. 아래 목록에서 "{topic_name}" 주제와 관련된 논문을 최대 2편 선별해주세요.

선별 기준:
- 키워드와 조금이라도 관련있으면 포함해주세요 (너무 엄격하게 판단하지 마세요)
- 최신 논문을 우선하되, 관련성이 더 중요합니다
- 반드시 최소 1편은 선택해야 합니다

논문 번호만 JSON 배열로 답해주세요. 예시: [1, 3]
다른 말은 하지 말고 JSON만 출력하세요.

논문 목록:
{paper_list}"""

    result = ask_groq(prompt)

    try:
        result = result.strip()
        indices = json.loads(result)
        selected = [papers[i - 1] for i in indices if 1 <= i <= len(papers)]
        return selected
    except Exception:
        return papers[:2]

def summarize_paper(paper):
    """논문 한국어 요약"""
    prompt = f"""Summarize the key content of the following paper in 2-3 sentences in Korean.

Title: {paper['title']}
Date: {paper['date']}
Abstract: {paper['abstract']}"""

    return ask_groq(prompt)

async def send_discord(session, message):
    """Discord 메시지 전송"""
    try:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": message[:2000]})
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Discord 전송 오류: {e}")

async def main():
    # 이미 본 논문 목록 불러오기
    seen_papers = load_seen_papers()
    new_seen_papers = set()

    async with aiohttp.ClientSession() as session:
        now = datetime.now().strftime("%Y-%m-%d")
        await send_discord(session, f"# 📚 Weekly Paper Report ({now})")

        for topic in TOPICS:
            topic_name = topic["name"]
            queries = topic["queries"]

            await send_discord(session, f"\n## 🔍 {topic_name}")

            # 1. 각 쿼리로 arxiv + OpenAlex 검색
            all_papers = []
            for query in queries:
                arxiv_papers = get_arxiv_papers(query, max_results=3)
                oa_papers = get_openalex_papers(query, max_results=3)
                all_papers.extend(arxiv_papers + oa_papers)

            # 2. 중복 제거
            all_papers = merge_and_deduplicate(all_papers)

            # 3. 이미 본 논문 제외
            new_papers = filter_new_papers(all_papers, seen_papers)

            if not new_papers:
                await send_discord(session, "ℹ️ 이번 주 새로운 논문 없음")
                continue

            await send_discord(
                session,
                f"📋 총 {len(new_papers)}편 새 논문 검색 완료 → AI 선별 중..."
            )

            # 4. Groq이 선별
            selected = select_papers(topic_name, new_papers)
            await send_discord(session, f"✅ {len(selected)}편 선별 완료\n")

            # 5. 선별된 논문 요약 + 전송
            for i, paper in enumerate(selected, 1):
                summary = summarize_paper(paper)
                message = (
                    f"**[{i}] {paper['title']}**\n"
                    f"📅 {paper['date']} | 📌 {paper['source']}\n"
                    f"{summary}\n"
                    f"🔗 <{paper['link']}>"
                )
                await send_discord(session, message)
                # 전송한 논문 링크 기록
                new_seen_papers.add(paper["link"])
                await asyncio.sleep(3)

        await send_discord(session, "\n🏁 Done!")

    # 새로 본 논문 저장
    seen_papers.update(new_seen_papers)
    save_seen_papers(seen_papers)
    print(f"✅ {len(new_seen_papers)}편 seen_papers.json에 저장 완료")

if __name__ == "__main__":
    asyncio.run(main())
