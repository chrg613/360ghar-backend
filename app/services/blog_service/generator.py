import json
from typing import List, Dict, Any, Tuple

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.blog import BlogPostCreate
from app.services.blog import create_blog_post
from app.utils.validators import ValidationUtils

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
        "You are an expert real estate content strategist for Gurgaon, writing for 360 Ghar "
        "(India's first VR-first real estate platform focused on verified, 360° virtual tours in Gurgaon). "
        "Write SEO-optimized, long-form blog posts with clear H2/H3 headings, short paragraphs, bullets, "
        "concrete local data/insights where helpful, and an engaging, trustworthy tone. "
        "Emphasize 360° virtual walkthroughs, verified listings, reduced site visits, Relationship Managers, "
        "and a modern, tech-enabled, broker-plus experience. Always stay focused on Gurgaon real estate. "
        "Return ONLY a valid JSON object with exactly the keys: title, content_html. "
        "Do NOT include markdown, code fences, or any explanation text around the JSON. "
        "content_html should be well-structured HTML suitable for direct rendering in a blog CMS."
    )

    user_prompt = (
        f"Research and write a high-quality blog post about: '{topic}'. "
        "Make it deeply specific to Gurgaon real estate (India) and the realities of buyers, tenants, and owners there in 2024/2025. "
        "Incorporate where appropriate: immersive 360° virtual tours, verified listings, fewer wasted visits, "
        "map-based discovery, and guided support from a Relationship Manager. "
        "Structure the article with: a strong intro, 3–6 key sections with H2/H3s, bullets or numbered lists where useful, "
        "4–6 Gurgaon-specific FAQs, and a clear conclusion with a soft CTA to explore homes on 360 Ghar. "
        "Use clean semantic HTML tags only (p, h2, h3, ul, ol, li, a, strong, em, blockquote)."
    )

    payload = {
        "model": settings.PERPLEXITY_MODEL or "sonar",
        "temperature": 0.7,
        "max_tokens": 8000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        # Always request structured JSON output via JSON Schema
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "blog_post",
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content_html": {"type": "string"},
                    },
                    "required": ["title", "content_html"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.error(f"Perplexity API error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perplexity generation failed")

        data = resp.json()

    # Perplexity uses OpenAI-like schema; extract structured JSON content
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        logger.error(f"Unexpected Perplexity response schema: {data}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Perplexity response")

    try:
        parsed = json.loads(content)
    except Exception as e:
        logger.error(f"Failed to parse Perplexity JSON content: {e} | content={content}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid JSON from Perplexity")

    if not isinstance(parsed, dict):
        logger.error(f"Perplexity JSON root is not an object: {parsed}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Perplexity JSON shape")

    title = parsed.get("title")
    content_html = parsed.get("content_html")

    if not title or not content_html:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perplexity did not return content")

    # Final HTML sanitization for safety
    safe_html = ValidationUtils.sanitize_html(content_html)

    return {"title": title.strip(), "content_html": safe_html}


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
        # Seed with brand- and city-aware categories/tags for 360 Ghar
        categories=["Gurgaon", "Real Estate", "Virtual Tours", "360 Ghar"],
        tags=["Gurgaon", "Real Estate", "Virtual Tours", "VR Real Estate", "360 Ghar"],
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
        "You create topical, SEO-aware content plans for Gurgaon-focused real estate blogs for 360 Ghar "
        "(India's first VR-first real estate platform with verified 360° virtual tours, no duplicate/misleading listings, "
        "and Relationship Manager support). "
        "You always think from the lens of buyers, tenants, and property owners in Gurgaon in 2024/2025."
    )
    prompt = (
        f"Generate {count} unique, high-intent blog topics about real estate in Gurgaon, India for 360 Ghar. "
        "Cover a diverse mix across buying and selling, renting, luxury and premium housing, investment trends, "
        "neighbourhood deep-dives (by sector/locality), legal and documentation guidance, and how VR/360° virtual tours "
        "plus verified listings and Relationship Managers change the property search journey. "
        "Each topic should be concise but specific (not just one-word), and sound natural for a blog article title. "
        "Return a JSON object of the shape: {\"topics\": [\"topic 1\", \"topic 2\", ...]}."
    )
    payload = {
        "model": settings.PERPLEXITY_MODEL or "sonar",
        "temperature": 0.6,
        "max_tokens": 8000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        # Always request structured JSON output via JSON Schema
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "blog_topics",
                "schema": {
                    "type": "object",
                    "properties": {
                        "topics": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["topics"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    }

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.error(f"Perplexity topic generation error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perplexity topic generation failed")
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        logger.error(f"Unexpected Perplexity response schema for topics: {data}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Perplexity response")

    try:
        parsed = json.loads(content)
    except Exception as e:
        logger.error(f"Failed to parse Perplexity topics JSON content: {e} | content={content}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid JSON from Perplexity")

    if not isinstance(parsed, dict):
        logger.error(f"Perplexity topics JSON root is not an object: {parsed}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Perplexity JSON shape")

    raw_topics = parsed.get("topics") or []
    if not isinstance(raw_topics, list):
        logger.error(f"Perplexity topics JSON 'topics' is not a list: {parsed}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Perplexity topics JSON")

    topics: List[str] = [str(t).strip() for t in raw_topics if str(t).strip()]

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
