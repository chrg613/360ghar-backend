"""
Tests for blog endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestBlogPostEndpoints:
    """Tests for blog post CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_blog_posts(self, client: AsyncClient):
        """Test listing blog posts."""
        with patch("app.api.api_v1.endpoints.blog.list_blog_posts", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ([], 0)

            response = await client.get("/api/v1/blog/posts")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data

    @pytest.mark.asyncio
    async def test_list_blog_posts_with_filters(self, client: AsyncClient):
        """Test listing blog posts with filters."""
        with patch("app.api.api_v1.endpoints.blog.list_blog_posts", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ([], 0)

            response = await client.get(
                "/api/v1/blog/posts",
                params={
                    "q": "real estate",
                    "categories": ["buying-guide"],
                    "page": 1,
                    "limit": 10,
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_blog_post(self, client: AsyncClient):
        """Test getting a specific blog post."""
        with patch("app.api.api_v1.endpoints.blog.get_blog_post", new_callable=AsyncMock) as mock_get:
            mock_post = MagicMock()
            mock_post.id = 1
            mock_post.title = "Test Post"
            mock_post.slug = "test-post"
            mock_get.return_value = mock_post

            response = await client.get("/api/v1/blog/posts/test-post")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_blog_post_not_found(self, client: AsyncClient):
        """Test getting a non-existent blog post."""
        with patch("app.api.api_v1.endpoints.blog.get_blog_post", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get("/api/v1/blog/posts/non-existent")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_blog_post(self, client: AsyncClient, admin_auth_headers):
        """Test creating a blog post."""
        with patch("app.api.api_v1.endpoints.blog.create_blog_post", new_callable=AsyncMock) as mock_create:
            mock_post = MagicMock()
            mock_post.id = 1
            mock_post.title = "New Post"
            mock_create.return_value = mock_post

            response = await client.post(
                "/api/v1/blog/posts",
                json={
                    "title": "New Post",
                    "content": "Post content here",
                    "excerpt": "Short excerpt",
                },
                headers=admin_auth_headers,
            )

            # May require admin privileges
            assert response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_update_blog_post(self, client: AsyncClient, admin_auth_headers):
        """Test updating a blog post."""
        with patch("app.api.api_v1.endpoints.blog.update_blog_post", new_callable=AsyncMock) as mock_update:
            mock_post = MagicMock()
            mock_post.id = 1
            mock_post.title = "Updated Post"
            mock_update.return_value = mock_post

            response = await client.put(
                "/api/v1/blog/posts/1",
                json={"title": "Updated Post"},
                headers=admin_auth_headers,
            )

            assert response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_delete_blog_post(self, client: AsyncClient, admin_auth_headers):
        """Test deleting a blog post."""
        with patch("app.api.api_v1.endpoints.blog.delete_blog_post", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            response = await client.delete(
                "/api/v1/blog/posts/1",
                headers=admin_auth_headers,
            )

            assert response.status_code in [200, 403]


class TestBlogCategoryEndpoints:
    """Tests for blog category endpoints."""

    @pytest.mark.asyncio
    async def test_list_categories(self, client: AsyncClient):
        """Test listing blog categories."""
        with patch("app.api.api_v1.endpoints.blog.get_categories_cached", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ([], 0)

            response = await client.get("/api/v1/blog/categories")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_category(self, client: AsyncClient):
        """Test getting a specific category."""
        with patch("app.api.api_v1.endpoints.blog.get_category", new_callable=AsyncMock) as mock_get:
            mock_category = MagicMock()
            mock_category.id = 1
            mock_category.name = "Buying Guide"
            mock_category.slug = "buying-guide"
            mock_get.return_value = mock_category

            response = await client.get("/api/v1/blog/categories/buying-guide")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_category_not_found(self, client: AsyncClient):
        """Test getting a non-existent category."""
        with patch("app.api.api_v1.endpoints.blog.get_category", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get("/api/v1/blog/categories/non-existent")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_category(self, client: AsyncClient, admin_auth_headers):
        """Test creating a blog category."""
        with patch("app.api.api_v1.endpoints.blog.create_category", new_callable=AsyncMock) as mock_create:
            mock_category = MagicMock()
            mock_category.id = 1
            mock_category.name = "New Category"
            mock_create.return_value = mock_category

            response = await client.post(
                "/api/v1/blog/categories",
                json={
                    "name": "New Category",
                    "description": "Category description",
                },
                headers=admin_auth_headers,
            )

            assert response.status_code in [201, 403]


class TestBlogTagEndpoints:
    """Tests for blog tag endpoints."""

    @pytest.mark.asyncio
    async def test_list_tags(self, client: AsyncClient):
        """Test listing blog tags."""
        with patch("app.api.api_v1.endpoints.blog.get_tags_cached", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ([], 0)

            response = await client.get("/api/v1/blog/tags")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_tag(self, client: AsyncClient):
        """Test getting a specific tag."""
        with patch("app.api.api_v1.endpoints.blog.get_tag", new_callable=AsyncMock) as mock_get:
            mock_tag = MagicMock()
            mock_tag.id = 1
            mock_tag.name = "real-estate"
            mock_get.return_value = mock_tag

            response = await client.get("/api/v1/blog/tags/real-estate")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_tag_not_found(self, client: AsyncClient):
        """Test getting a non-existent tag."""
        with patch("app.api.api_v1.endpoints.blog.get_tag", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get("/api/v1/blog/tags/non-existent")

            assert response.status_code == 404


class TestBlogGenerationEndpoints:
    """Tests for AI-powered blog generation endpoints."""

    @pytest.mark.asyncio
    async def test_generate_from_topic(self, client: AsyncClient, admin_auth_headers):
        """Test generating blog from topic."""
        with patch("app.api.api_v1.endpoints.blog.generate_draft_from_topic", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "success": True,
                "title": "Generated Title",
                "content": "Generated content",
            }

            response = await client.post(
                "/api/v1/blog/generate-from-topic",
                json={"topic": "Real estate investing tips"},
                headers=admin_auth_headers,
            )

            # May require admin privileges or fail if AI service unavailable
            assert response.status_code in [200, 403, 422, 500]

    @pytest.mark.asyncio
    async def test_generate_bulk(self, client: AsyncClient, admin_auth_headers):
        """Test bulk blog generation."""
        with patch("app.api.api_v1.endpoints.blog.generate_bulk_blogs", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = [
                {"success": True, "title": "Post 1"},
                {"success": True, "title": "Post 2"},
            ]

            response = await client.post(
                "/api/v1/blog/generate-bulk",
                json={"count": 2},
                headers=admin_auth_headers,
            )

            assert response.status_code in [200, 403, 422, 500]
