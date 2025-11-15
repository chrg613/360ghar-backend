import json
from typing import List, Dict, Any, Tuple

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.blog import BlogPostCreate
from app.services.blog import create_blog_post

logger = get_logger(__name__)


def _build_excerpt_from_html(html: str, max_len: int = 280) -> str:
    try:
        import re
        # Strip tags quickly; we don't need perfect HTML parsing for an excerpt
        text = re.sub(r"<[^>]+>", " ", html or "")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_len].rstrip()
    except Exception:
        return (html or "")[:max_len]


async def _perplexity_generate(topic: str) -> Dict[str, str]:
    if not settings.PERPLEXITY_API_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PERPLEXITY_API_KEY not configured")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    system = (
        "You are an expert real estate content strategist for the Gurgaon market. "
        "Write SEO-optimized long-form blog posts with clear H2/H3 headings, short paragraphs, bullets, "
        "data points where helpful, and an engaging tone. Always focus on real estate in Gurgaon. "
        "Return ONLY valid JSON with keys: title, content_html. content_html must be sanitized HTML." 
    )

    user_prompt = (
        f"Research and write a high-quality blog post about: '{topic}'. "
        "Make it specific to Gurgaon real estate (India). Include: intro, key sections, insights, 4-6 FAQs, and a conclusion. "
        "Use semantic headings and internal structure suitable for a CMS."
    )

    payload = {
        "model": settings.PERPLEXITY_MODEL or "sonar",
        "temperature": 0.7,
        "max_tokens": 8000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.error(f"Perplexity API error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perplexity generation failed")

        data = resp.json()

    # Perplexity uses OpenAI-like schema; extract content string
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        logger.error(f"Unexpected Perplexity response schema: {data}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Perplexity response")

    # Try to parse JSON content
    try:
        parsed = json.loads(content)
        title = parsed.get("title")
        content_html = parsed.get("content_html")
    except Exception:
        # Fallback: naive parsing – take first line as title, remainder as HTML
        lines = (content or "").splitlines()
        title = (lines[0] if lines else topic).strip().strip('"')
        content_html = "\n".join(lines[1:]) or content

    if not title or not content_html:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perplexity did not return content")

    return {"title": title.strip(), "content_html": content_html}


async def _serpapi_image_search(query: str, count: int = 5) -> List[str]:
    """
    Best-effort image search using SerpAPI's Google Images engine.
    Returns a list of direct image URLs (original where possible).
    """
    if not settings.SERPAPI_API_KEY:
        logger.warning("SERPAPI_API_KEY not configured; skipping image search")
        return []

    # Clamp requested count between 1 and 10 for safety
    count = min(max(count, 1), 10)

    params = {
        "engine": "google_images",
        "q": query,
        "api_key": settings.SERPAPI_API_KEY,
        # Localize to India / English for Gurgaon-focused content
        "google_domain": "google.co.in",
        "gl": "in",
        "hl": "en",
        # Enable SafeSearch on Google Images
        "safe": "active",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(settings.SERPAPI_SEARCH_ENDPOINT, params=params)
        if resp.status_code >= 400:
            logger.error(f"SerpAPI Google Images error {resp.status_code}: {resp.text}")
            return []
        data = resp.json()

    # SerpAPI Google Images returns results under "images_results"
    values = data.get("images_results") or []
    urls: List[str] = []
    for item in values:
        # Prefer full-size image when available, otherwise thumbnail
        url = item.get("original") or item.get("thumbnail")
        if url:
            urls.append(url)
        if len(urls) >= count:
            break
    return urls


async def generate_draft_from_topic(db, *, topic: str, actor) -> Dict[str, Any]:
    # Generate title + content
    result = await _perplexity_generate(topic)
    title = result["title"]
    content_html = result["content_html"]

    # Find images (best effort)
    images = await _serpapi_image_search(f"{topic} Gurgaon real estate")
    cover_image = images[0] if images else None

    # Build excerpt
    excerpt = _build_excerpt_from_html(content_html)

    # Persist as draft
    payload = BlogPostCreate(
        title=title,
        content=content_html,
        excerpt=excerpt,
        cover_image_url=cover_image,
        categories=["Gurgaon", "Real Estate"],
        tags=["Gurgaon", "Real Estate"],
        active=False,
    )

    created = await create_blog_post(db, payload, actor)

    return {"blog": created, "images": images}


async def generate_bulk_blogs(db, *, count: int, actor) -> List[Dict[str, Any]]:
    # Generate topic ideas first
    if not settings.PERPLEXITY_API_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PERPLEXITY_API_KEY not configured")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    system = (
        "You create topical content plans for Gurgaon real estate. "
        "Return ONLY JSON array 'topics' with unique, specific blog topics."
    )
    prompt = (
        f"Generate {count} unique blog topics about real estate in Gurgaon. "
        "Make them specific and current (2024/2025), diverse across buying, renting, luxury, investment, neighbourhoods, and legal. "
        "Return JSON of the shape: {\"topics\": [\"...\"]}"
    )
    payload = {
        "model": settings.PERPLEXITY_MODEL or "sonar",
        "temperature": 0.6,
        "max_tokens": 8000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.error(f"Perplexity topic generation error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perplexity topic generation failed")
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        topics = parsed.get("topics") or []
    except Exception:
        logger.warning("Falling back to newline-split topics parsing")
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        topics = [t.strip("- •\n ") for t in text.splitlines() if t.strip()]

    # Deduplicate and cap to requested count
    uniq: List[str] = []
    seen = set()
    for t in topics:
        key = t.lower().strip()
        if key and key not in seen:
            uniq.append(t)
            seen.add(key)
        if len(uniq) >= count:
            break

    results: List[Dict[str, Any]] = []
    for t in uniq:
        try:
            draft = await generate_draft_from_topic(db, topic=t, actor=actor)
            results.append(draft)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate draft for topic '{t}': {e}")
    return results
