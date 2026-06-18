from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models.blogs import BlogCategory, BlogPost, BlogTag

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def blog_client(test_app, db_session) -> AsyncClient:
    """Public client (no auth needed for blog reads)."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as ac:
        yield ac


@pytest_asyncio.fixture
async def three_posts(db_session) -> list[BlogPost]:
    """3 active blog posts with distinct created_at (via flush order)."""
    posts = []
    base = datetime.now(timezone.utc)
    for i in range(3):
        post = BlogPost(
            title=f"Pagination Post {i}",
            slug=f"pagination-post-{i}-{uuid.uuid4().hex[:6]}",
            content="Content " * 10,
            active=True,
            published_at=base - timedelta(days=i),
        )
        db_session.add(post)
        await db_session.flush()
        await db_session.refresh(post)
        posts.append(post)
    return posts


@pytest_asyncio.fixture
async def three_categories(db_session) -> list[BlogCategory]:
    """3 blog categories with distinct names (alphabetical order: Alpha, Beta, Gamma)."""
    categories = []
    for name in ["Alpha Category", "Beta Category", "Gamma Category"]:
        cat = BlogCategory(name=name, slug=name.lower().replace(" ", "-"))
        db_session.add(cat)
        await db_session.flush()
        await db_session.refresh(cat)
        categories.append(cat)
    return categories


@pytest_asyncio.fixture
async def three_tags(db_session) -> list[BlogTag]:
    """3 blog tags with distinct names."""
    tags = []
    for name in ["Alpha Tag", "Beta Tag", "Gamma Tag"]:
        tag = BlogTag(name=name, slug=name.lower().replace(" ", "-"))
        db_session.add(tag)
        await db_session.flush()
        await db_session.refresh(tag)
        tags.append(tag)
    return tags


async def test_posts_cursor_paginates(blog_client: AsyncClient, three_posts: list[BlogPost]) -> None:
    r1 = await blog_client.get("/api/v1/blog/posts?limit=2")
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert set(b1) >= {"items", "next_cursor", "has_more", "limit"}
    assert len(b1["items"]) == 2
    assert b1["has_more"] is True
    assert b1["next_cursor"]

    r2 = await blog_client.get(f"/api/v1/blog/posts?limit=2&cursor={b1['next_cursor']}")
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    ids1 = {item["id"] for item in b1["items"]}
    ids2 = {item["id"] for item in b2["items"]}
    assert ids1.isdisjoint(ids2)
    assert b2["has_more"] is False
    assert b2["next_cursor"] is None


async def test_posts_include_total(blog_client: AsyncClient, three_posts: list[BlogPost]) -> None:
    r = await blog_client.get("/api/v1/blog/posts?limit=2&include_total=true")
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 3


async def test_posts_invalid_cursor_400(blog_client: AsyncClient) -> None:
    r = await blog_client.get("/api/v1/blog/posts?cursor=garbage!!!")
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "INVALID_CURSOR"


async def test_categories_cursor_paginates(blog_client: AsyncClient, three_categories: list[BlogCategory]) -> None:
    r1 = await blog_client.get("/api/v1/blog/categories?limit=2")
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert set(b1) >= {"items", "next_cursor", "has_more", "limit"}
    assert len(b1["items"]) == 2
    assert b1["has_more"] is True
    # Verify ASC order
    names = [item["name"] for item in b1["items"]]
    assert names == sorted(names)

    r2 = await blog_client.get(f"/api/v1/blog/categories?limit=2&cursor={b1['next_cursor']}")
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    ids1 = {item["id"] for item in b1["items"]}
    ids2 = {item["id"] for item in b2["items"]}
    assert ids1.isdisjoint(ids2)
    assert b2["has_more"] is False


async def test_categories_include_total(blog_client: AsyncClient, three_categories: list[BlogCategory]) -> None:
    r = await blog_client.get("/api/v1/blog/categories?limit=2&include_total=true")
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 3


async def test_categories_invalid_cursor_400(blog_client: AsyncClient) -> None:
    r = await blog_client.get("/api/v1/blog/categories?cursor=garbage!!!")
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "INVALID_CURSOR"


async def test_tags_cursor_paginates(blog_client: AsyncClient, three_tags: list[BlogTag]) -> None:
    r1 = await blog_client.get("/api/v1/blog/tags?limit=2")
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert set(b1) >= {"items", "next_cursor", "has_more", "limit"}
    assert len(b1["items"]) == 2
    assert b1["has_more"] is True
    # Verify ASC order
    names = [item["name"] for item in b1["items"]]
    assert names == sorted(names)

    r2 = await blog_client.get(f"/api/v1/blog/tags?limit=2&cursor={b1['next_cursor']}")
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    ids1 = {item["id"] for item in b1["items"]}
    ids2 = {item["id"] for item in b2["items"]}
    assert ids1.isdisjoint(ids2)
    assert b2["has_more"] is False


async def test_tags_include_total(blog_client: AsyncClient, three_tags: list[BlogTag]) -> None:
    r = await blog_client.get("/api/v1/blog/tags?limit=2&include_total=true")
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 3


async def test_tags_invalid_cursor_400(blog_client: AsyncClient) -> None:
    r = await blog_client.get("/api/v1/blog/tags?cursor=garbage!!!")
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "INVALID_CURSOR"
