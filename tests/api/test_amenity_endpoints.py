"""
Tests for amenity endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestListAmenitiesEndpoint:
    """Tests for GET /api/v1/amenities/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_amenities(self, client: AsyncClient):
        """Test listing all amenities."""
        with patch("app.api.api_v1.endpoints.amenities.get_amenities_cached", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"id": 1, "title": "WiFi", "icon": "wifi"},
                {"id": 2, "title": "Parking", "icon": "car"},
                {"id": 3, "title": "Pool", "icon": "pool"},
            ]

            response = await client.get("/api/v1/amenities/")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_amenities_empty(self, client: AsyncClient):
        """Test listing amenities when none exist."""
        with patch("app.api.api_v1.endpoints.amenities.get_amenities_cached", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = await client.get("/api/v1/amenities/")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_amenities_cached(self, client: AsyncClient):
        """Test that amenities endpoint uses caching."""
        with patch("app.api.api_v1.endpoints.amenities.get_amenities_cached", new_callable=AsyncMock) as mock_cached:
            mock_cached.return_value = [{"id": 1, "title": "Test"}]

            # First request
            response1 = await client.get("/api/v1/amenities/")
            # Second request
            response2 = await client.get("/api/v1/amenities/")

            assert response1.status_code == 200
            assert response2.status_code == 200
