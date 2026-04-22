import os
import random
import requests
import tempfile
import asyncio
import aiohttp
import re
from urllib.parse import quote

# 환경 변수
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ZOTERO_DISCORD_WEBHOOK_URL = os.getenv("ZOTERO_DISCORD_WEBHOOK_URL")
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID")
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL")

ZOTERO_BASE = f"https://api.zotero.org/users/{ZOTERO_USER_ID}"
HEADERS = {
    "Zotero-API-Key": ZOTERO_API_KEY,
    "Content-Type": "application/json"
}
READ_TAG = "BOT"
EXCLUDE_TAGS = {"BOT", "✅Read"}

def ask_groq(prompt_text):
    """Groq API 호출"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.3
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res_data = res.json()
        if "error" in res_data:
            return f"❌ Groq 에러: {res_data['error'].get('message', 'Unknown')}"
        return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ 통신 오류: {str(e)}"

def get_unread_papers():
    """Zotero에서 읽지 않은 논문 랜덤 1편 가져오기"""
    try:
        res = requests.get(
            f"{ZOTERO_BASE}/items",
            headers=HEADERS,
            params={
                "itemType": "journalArticle || preprint || conferencePaper",
                "limit": 50,
                "sort": "dateAdded",
                "direction": "asc"
            }
        )
        items = res.json()

        unread = []
        for item in items:
            tags = [t["tag"] for t in item["data"].get("tags", [])]
            if not any(tag in EXCLUDE_TAGS for tag in tags):
                unread.append(item)

        return random.choice(unread) if unread else None
    except Exception as e:
        print(f"Zotero 오류: {e}")
        return None

def extract_text_from_pdf_bytes(pdf_bytes, max_pages=12, max_chars=14000):
    """PDF 바이너리에서 텍스트 추출"""
    try:
        import fitz  # pymupdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            tmp_path = f.name

        doc = fitz.open(tmp_path)
        text = ""
        for page in doc[:max_pages]:
            text += page.get_text()
        doc.close()
        os.unlink(tmp_path)

        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:max_chars] if text.strip() else None
    except Exception as e:
        print(f"PDF 추출 오류: {e}")
        return None

def get_pdf_text_from_url(pdf_url):
    """PDF URL에서 텍스트 추출"""
    try:
        res = requests.get(
            pdf_url,
            timeout=40,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if res.status_code != 200 or not res.content:
            return None
        return extract_text_from_pdf_bytes(res.content)
    except Exception as e:
        print(f"PDF 다운로드 오류: {e}")
        return None

def find_arxiv_id(item_data):
    """Zotero 아이템에서 arXiv ID 찾기"""
    # DOI에서 찾기
    doi = item_data.get("DOI", "")
    if "arxiv" in doi.lower():
        return doi.split("/")[-1]

    # URL에서 찾기
    url = item_data.get("url", "")
    if "arxiv.org" in url:
        parts = url.rstrip("/").split("/")
        return parts[-1]

    # extra 필드에서 찾기
    extra = item_data.get("extra", "")
    for line in extra.split("\n"):
        if "arxiv" in line.lower():
            parts = line.split(":")
            if len(parts) > 1:
                return parts[-1].strip()

    return None

def find_pmid_or_pmcid(item_data):
    """Zotero 메타데이터에서 PMID/PMCID 추출"""
    combined = "\n".join([
        item_data.get("extra", ""),
        item_data.get("url", ""),
        item_data.get("DOI", "")
    ])

    pmcid_match = re.search(r"\bPMC\d+\b", combined, re.IGNORECASE)
    if pmcid_match:
        return None, pmcid_match.group(0).upper()

    pmid_match = re.search(r"PMID[:\s]+(\d+)", combined, re.IGNORECASE)
    if pmid_match:
        return pmid_match.group(1), None

    return None, None

def get_pubmed_central_pdf_url(item_data):
    """PubMed Central PDF URL 찾기"""
    pmid, pmcid = find_pmid_or_pmcid(item_data)

    if not pmcid and pmid:
        try:
            res = requests.get(
                f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={pmid}&format=json",
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = res.json()
            records = data.get("records", [])
            if records and records[0].get("pmcid"):
                pmcid = records[0]["pmcid"]
        except Exception as e:
            print(f"PMCID 변환 오류: {e}")

    if pmcid:
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/"

    return None

def get_unpaywall_pdf_url(doi):
    """Unpaywall에서 OA PDF URL 찾기"""
    if not doi or not UNPAYWALL_EMAIL:
        return None

    try:
        res = requests.get(
            f"https://api.unpaywall.org/v2/{quote(doi)}",
            params={"email": UNPAYWALL_EMAIL},
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if res.status_code != 200:
            return None

        data = res.json()
        best = data.get("best_oa_location") or {}
        if best.get("url_for_pdf"):
            return best["url_for_pdf"]

        for location in data.get("oa_locations", []):
            if location.get("url_for_pdf"):
                return location["url_for_pdf"]
    except Exception as e:
        print(f"Unpaywall 조회 오류: {e}")

    return None

def collect_full_text_sources(item_data):
    """시도할 원문 PDF 소스 목록 생성"""
    sources = []
    seen = set()

    url = item_data.get("url", "").strip()
    doi = item_data.get("DOI", "").strip()

    if url.lower().endswith(".pdf"):
        sources.append(("direct_pdf", url))

    arxiv_id = find_arxiv_id(item_data)
    if arxiv_id:
        sources.append(("arxiv", f"https://arxiv.org/pdf/{arxiv_id}"))

    pmc_pdf_url = get_pubmed_central_pdf_url(item_data)
    if pmc_pdf_url:
        sources.append(("pmc", pmc_pdf_url))

    unpaywall_pdf_url = get_unpaywall_pdf_url(doi)
    if unpaywall_pdf_url:
        sources.append(("unpaywall", unpaywall_pdf_url))

    deduped_sources = []
    for source_name, source_url in sources:
        if source_url and source_url not in seen:
            seen.add(source_url)
            deduped_sources.append((source_name, source_url))

    return deduped_sources

def mark_as_read(item_key, item_version, current_tags):
    """Zotero 아이템에 읽음 태그 추가"""
    try:
        new_tags = current_tags + [{"tag": READ_TAG}]
        res = requests.patch(
            f"{ZOTERO_BASE}/items/{item_key}",
            headers={**HEADERS, "If-Unmodified-Since-Version": str(item_version)},
            json={"tags": new_tags}
        )
        return res.status_code == 204
    except Exception as e:
        print(f"태그 추가 오류: {e}")
        return False

def summarize_paper(title, content, is_full_text=False):
    """논문 요약"""
    source = "full paper text" if is_full_text else "abstract"
    prompt = f"""You are an expert in photonics and laser physics. 
Summarize the following paper based on its {source}.

Title: {title}

Content:
{content}

Please provide:
1. **핵심 질문** (1-2문장): 이 논문이 해결하려는 문제는 무엇인가?
2. **핵심 결과** (3-4문장): 무엇을 달성했고, 수치나 비교 우위가 있으면 포함.
3. **방법/실험 구성** (2-3문장): 어떤 장치, 데이터, 실험 설계를 썼는가?
4. **의의** (2문장): 왜 중요한가?
5. **한계 또는 주의점** (1-2문장): 본문에 보이는 제약, 가정, 일반화 한계.
6. **한줄 결론** (1문장): 가장 중요한 takeaway.

Be concise, technical, and specific. If the source is only an abstract, state uncertainty conservatively and do not invent details.

Please in Korean"""

    return ask_groq(prompt)

async def send_discord(session, message):
    """Discord 메시지 전송"""
    try:
        await session.post(ZOTERO_DISCORD_WEBHOOK_URL, json={"content": message[:2000]})
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Discord 전송 오류: {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        await send_discord(session, "📖 **Zotero 읽기 알림**")

        # 1. 읽지 않은 논문 1편 가져오기
        item = get_unread_papers()
        if not item:
            await send_discord(session, "✅ 읽지 않은 논문이 없어요!")
            return

        item_data = item["data"]
        item_key = item["key"]
        item_version = item["version"]
        current_tags = item_data.get("tags", [])

        title = item_data.get("title", "제목 없음")
        abstract = item_data.get("abstractNote", "")
        authors = ", ".join([
            a.get("lastName", "") for a in item_data.get("creators", [])[:3]
        ])
        year = item_data.get("date", "")[:4]
        journal = item_data.get("publicationTitle", "") or item_data.get("proceedingsTitle", "")

        await send_discord(session, f"📄 **{title}**\n👥 {authors} ({year}) | {journal}")

        # 2. 다양한 플랫폼에서 원문 PDF 시도
        summary = None
        full_text_sources = collect_full_text_sources(item_data)

        if full_text_sources:
            await send_discord(
                session,
                "🔍 원문 PDF 탐색 중... "
                + ", ".join(source_name for source_name, _ in full_text_sources)
            )

        for source_name, pdf_url in full_text_sources:
            print(f"{source_name} PDF 시도: {pdf_url}")
            pdf_text = get_pdf_text_from_url(pdf_url)
            if not pdf_text:
                continue

            await send_discord(session, f"✅ `{source_name}` 원문 확보! 상세 요약 중...")
            summary = summarize_paper(title, pdf_text, is_full_text=True)
            summary = f"📑 **원문 기반 상세 요약** (`{source_name}`)\n{summary}"
            break

        if full_text_sources and not summary:
            await send_discord(session, "⚠️ 원문 PDF 확보 실패, 초록으로 요약합니다.")

        # 3. PDF 실패 또는 원문 소스 없으면 → 초록으로 요약
        if not summary:
            if abstract:
                await send_discord(session, "📝 초록 기반 상세 요약 중...")
                summary = summarize_paper(title, abstract, is_full_text=False)
                summary = f"📝 **초록 기반 상세 요약**\n{summary}"
            else:
                summary = "⚠️ 초록이 없어서 요약할 수 없어요."

        await send_discord(session, summary)

        # 4. Zotero에 읽음 태그 추가
        success = mark_as_read(item_key, item_version, current_tags)
        if success:
            await send_discord(session, f"✅ Zotero에 `{READ_TAG}` 태그 추가 완료!")
        else:
            await send_discord(session, f"⚠️ Zotero 태그 추가 실패. 수동으로 추가해주세요.")

        # 5. 링크 전송
        url = item_data.get("url", "")
        doi = item_data.get("DOI", "")
        link = url or (f"https://doi.org/{doi}" if doi else "링크 없음")
        await send_discord(session, f"🔗 {link}")

if __name__ == "__main__":
    asyncio.run(main())
