"""
Tests for core endpoints (health, config, etc.).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or data.get("ok") is True


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")

        assert response.status_code == 200


class TestDocsEndpoint:
    """Tests for documentation endpoints."""

    @pytest.mark.asyncio
    async def test_swagger_docs(self, client: AsyncClient):
        """Test Swagger UI endpoint."""
        response = await client.get("/api/v1/docs")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc(self, client: AsyncClient):
        """Test ReDoc endpoint."""
        response = await client.get("/api/v1/redoc")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json(self, client: AsyncClient):
        """Test OpenAPI JSON endpoint."""
        response = await client.get("/api/v1/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data


class TestCitiesEndpoint:
    """Tests for GET /api/v1/core/cities endpoint."""

    @pytest.mark.asyncio
    async def test_get_cities(self, client: AsyncClient):
        """Test getting available cities."""
        with patch("app.api.api_v1.endpoints.core.get_available_cities", new_callable=AsyncMock) as mock_cities:
            mock_cities.return_value = ["Mumbai", "Delhi", "Bangalore"]

            response = await client.get("/api/v1/core/cities")

            assert response.status_code == 200


class TestLocalitiesEndpoint:
    """Tests for GET /api/v1/core/localities endpoint."""

    @pytest.mark.asyncio
    async def test_get_localities(self, client: AsyncClient):
        """Test getting localities for a city."""
        with patch("app.api.api_v1.endpoints.core.get_localities_for_city", new_callable=AsyncMock) as mock_localities:
            mock_localities.return_value = ["Andheri", "Bandra", "Powai"]

            response = await client.get(
                "/api/v1/core/localities",
                params={"city": "Mumbai"},
            )

            assert response.status_code == 200


class TestPropertyTypesEndpoint:
    """Tests for GET /api/v1/core/property-types endpoint."""

    @pytest.mark.asyncio
    async def test_get_property_types(self, client: AsyncClient):
        """Test getting property types."""
        response = await client.get("/api/v1/core/property-types")

        assert response.status_code == 200


class TestAmenitiesListEndpoint:
    """Tests for GET /api/v1/amenities/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_amenities(self, client: AsyncClient):
        """Test getting available amenities."""
        with patch("app.api.api_v1.endpoints.amenities.get_all_amenities", new_callable=AsyncMock) as mock_amenities:
            mock_amenities.return_value = [
                {"id": 1, "title": "WiFi"},
                {"id": 2, "title": "Parking"},
            ]

            response = await client.get("/api/v1/amenities/")

            assert response.status_code == 200
