import os
import random
import requests
import json
import tempfile
import asyncio
import aiohttp

# 환경 변수
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ZOTERO_DISCORD_WEBHOOK_URL = os.getenv("ZOTERO_DISCORD_WEBHOOK_URL")
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID")

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

def get_arxiv_pdf_text(arxiv_id):
    """arXiv PDF에서 텍스트 추출"""
    try:
        import fitz  # pymupdf
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        res = requests.get(pdf_url, timeout=30)
        if res.status_code != 200:
            return None

        # 임시 파일에 저장 후 텍스트 추출
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(res.content)
            tmp_path = f.name

        doc = fitz.open(tmp_path)
        text = ""
        for page in doc[:10]:  # 최대 10페이지만
            text += page.get_text()
        doc.close()
        os.unlink(tmp_path)

        return text[:8000] if text else None  # Groq 토큰 제한
    except Exception as e:
        print(f"PDF 추출 오류: {e}")
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
1. **Key Findings** (2-3 sentences): What did they discover or achieve?
2. **Methods** (1-2 sentences): How did they do it?
3. **Significance** (1-2 sentences): Why does this matter?

Be concise and technical. 

Please in Korean"""

    return ask_groq(prompt)

async def send_discord(session, message):
    """Discord 메시지 전송"""
    try:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": message[:2000]})
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

        # 2. arXiv PDF 원문 시도
        arxiv_id = find_arxiv_id(item_data)
        summary = None

        if arxiv_id:
            print(f"arXiv ID 발견: {arxiv_id}")
            await send_discord(session, f"🔍 arXiv 원문 읽는 중... (`{arxiv_id}`)")
            pdf_text = get_arxiv_pdf_text(arxiv_id)

            if pdf_text:
                await send_discord(session, "✅ 원문 PDF 읽기 성공! 요약 중...")
                summary = summarize_paper(title, pdf_text, is_full_text=True)
                summary = f"📑 **원문 기반 요약**\n{summary}"
            else:
                await send_discord(session, "⚠️ PDF 읽기 실패, 초록으로 요약합니다.")

        # 3. PDF 실패 또는 arXiv 아닌 경우 → 초록으로 요약
        if not summary:
            if abstract:
                await send_discord(session, "📝 초록으로 요약 중...")
                summary = summarize_paper(title, abstract, is_full_text=False)
                summary = f"📝 **초록 기반 요약**\n{summary}"
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
