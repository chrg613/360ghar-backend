"""
Tests for swipe endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestRecordSwipeEndpoint:
    """Tests for POST /api/v1/swipes/ endpoint."""

    @pytest.mark.asyncio
    async def test_record_swipe_like(self, client: AsyncClient, auth_headers, test_property):
        """Test recording a like swipe."""
        with patch("app.api.api_v1.endpoints.swipes.record_swipe", new_callable=AsyncMock) as mock_swipe:
            mock_swipe.return_value = True

            response = await client.post(
                "/api/v1/swipes/",
                json={
                    "property_id": test_property.id,
                    "is_liked": True,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_record_swipe_dislike(self, client: AsyncClient, auth_headers, test_property):
        """Test recording a dislike swipe."""
        with patch("app.api.api_v1.endpoints.swipes.record_swipe", new_callable=AsyncMock) as mock_swipe:
            mock_swipe.return_value = True

            response = await client.post(
                "/api/v1/swipes/",
                json={
                    "property_id": test_property.id,
                    "is_liked": False,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_record_swipe_unauthorized(self, client: AsyncClient, test_property):
        """Test swipe without auth."""
        response = await client.post(
            "/api/v1/swipes/",
            json={
                "property_id": test_property.id,
                "is_liked": True,
            },
        )

        assert response.status_code == 401


class TestGetSwipeHistoryEndpoint:
    """Tests for GET /api/v1/swipes/history endpoint."""

    @pytest.mark.asyncio
    async def test_get_swipe_history(self, client: AsyncClient, auth_headers):
        """Test getting swipe history."""
        with patch("app.api.api_v1.endpoints.swipes.get_swipe_history", new_callable=AsyncMock) as mock_history:
            mock_history.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "limit": 20,
                "total_pages": 0,
            }

            response = await client.get(
                "/api/v1/swipes/history",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data

    @pytest.mark.asyncio
    async def test_get_swipe_history_liked_only(self, client: AsyncClient, auth_headers):
        """Test getting only liked swipes."""
        with patch("app.api.api_v1.endpoints.swipes.get_swipe_history", new_callable=AsyncMock) as mock_history:
            mock_history.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "limit": 20,
                "total_pages": 0,
            }

            response = await client.get(
                "/api/v1/swipes/history",
                params={"is_liked": "true"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestUndoSwipeEndpoint:
    """Tests for DELETE /api/v1/swipes/undo endpoint."""

    @pytest.mark.asyncio
    async def test_undo_last_swipe(self, client: AsyncClient, auth_headers):
        """Test undoing last swipe."""
        with patch("app.api.api_v1.endpoints.swipes.undo_last_swipe", new_callable=AsyncMock) as mock_undo:
            mock_swipe = MagicMock()
            mock_swipe.id = 1
            mock_swipe.property_id = 1
            mock_undo.return_value = mock_swipe

            response = await client.delete(
                "/api/v1/swipes/undo",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_undo_swipe_no_swipes(self, client: AsyncClient, auth_headers):
        """Test undoing when no swipes exist."""
        with patch("app.api.api_v1.endpoints.swipes.undo_last_swipe", new_callable=AsyncMock) as mock_undo:
            mock_undo.return_value = None

            response = await client.delete(
                "/api/v1/swipes/undo",
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestToggleSwipeEndpoint:
    """Tests for PATCH /api/v1/swipes/{swipe_id}/toggle endpoint."""

    @pytest.mark.asyncio
    async def test_toggle_swipe_success(self, client: AsyncClient, auth_headers, test_swipe):
        """Test toggling swipe status."""
        with patch("app.api.api_v1.endpoints.swipes.toggle_swipe", new_callable=AsyncMock) as mock_toggle:
            mock_toggle.return_value = {"new_status": True, "property_id": 1}

            response = await client.patch(
                f"/api/v1/swipes/{test_swipe.id}/toggle",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "new_status" in data

    @pytest.mark.asyncio
    async def test_toggle_swipe_not_found(self, client: AsyncClient, auth_headers):
        """Test toggling non-existent swipe."""
        with patch("app.api.api_v1.endpoints.swipes.toggle_swipe", new_callable=AsyncMock) as mock_toggle:
            mock_toggle.return_value = None

            response = await client.patch(
                "/api/v1/swipes/99999/toggle",
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestGetSwipeStatsEndpoint:
    """Tests for GET /api/v1/swipes/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_swipe_stats(self, client: AsyncClient, auth_headers):
        """Test getting swipe statistics."""
        with patch("app.api.api_v1.endpoints.swipes.get_swipe_stats", new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = {
                "total_swipes": 100,
                "liked_count": 60,
                "disliked_count": 40,
                "like_percentage": 60.0,
            }

            response = await client.get(
                "/api/v1/swipes/stats",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "total_swipes" in data
            assert "like_percentage" in data


class TestGetLikesEndpoint:
    """Tests for GET /api/v1/swipes/likes endpoint."""

    @pytest.mark.asyncio
    async def test_get_likes(self, client: AsyncClient, auth_headers):
        """Test getting liked properties."""
        with patch("app.api.api_v1.endpoints.swipes.get_swipe_history", new_callable=AsyncMock) as mock_likes:
            mock_likes.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "limit": 20,
                "total_pages": 0,
            }

            response = await client.get(
                "/api/v1/swipes/likes",
                headers=auth_headers,
            )

            assert response.status_code == 200
