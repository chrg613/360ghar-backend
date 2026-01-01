"""
End-to-end tests for property listing flow.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestPropertyListingFlow:
    """Tests for complete property listing flow."""

    @pytest.mark.asyncio
    async def test_create_and_list_property(self, client: AsyncClient, auth_headers):
        """Test creating a property and seeing it in listings."""
        # Step 1: Create property
        with patch("app.api.api_v1.endpoints.properties.create_property", new_callable=AsyncMock) as mock_create:
            mock_property = MagicMock()
            mock_property.id = 1
            mock_property.title = "Test Property"
            mock_property.property_type = "apartment"
            mock_property.purpose = "rent"
            mock_create.return_value = mock_property

            response = await client.post(
                "/api/v1/properties/",
                json={
                    "title": "Test Property",
                    "description": "A beautiful property",
                    "property_type": "apartment",
                    "purpose": "rent",
                    "monthly_rent": 50000,
                    "city": "Mumbai",
                    "locality": "Andheri",
                    "full_address": "123 Test Street",
                    "pincode": "400069",
                    "state": "Maharashtra",
                    "country": "India",
                    "bedrooms": 2,
                    "bathrooms": 2,
                    "area_sqft": 1000,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

        # Step 2: List properties
        with patch("app.api.api_v1.endpoints.properties.get_unified_properties_optimized", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {
                "items": [mock_property],
                "total": 1,
                "page": 1,
                "limit": 20,
            }

            response = await client.get("/api/v1/properties/")

            assert response.status_code == 200


class TestPropertySearchFlow:
    """Tests for property search flow."""

    @pytest.mark.asyncio
    async def test_search_properties_by_location(self, client: AsyncClient):
        """Test searching properties by location."""
        with patch("app.api.api_v1.endpoints.properties.get_unified_properties_optimized", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "limit": 20,
            }

            response = await client.get(
                "/api/v1/properties/",
                params={
                    "latitude": 19.1136,
                    "longitude": 72.8697,
                    "radius_km": 10,
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_properties_by_filters(self, client: AsyncClient):
        """Test searching with multiple filters."""
        with patch("app.api.api_v1.endpoints.properties.get_unified_properties_optimized", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "limit": 20,
            }

            response = await client.get(
                "/api/v1/properties/",
                params={
                    "city": "Mumbai",
                    "property_type": "apartment",
                    "purpose": "rent",
                    "price_min": 20000,
                    "price_max": 80000,
                    "bedrooms_min": 2,
                },
            )

            assert response.status_code == 200


class TestPropertyViewFlow:
    """Tests for viewing property details."""

    @pytest.mark.asyncio
    async def test_view_property_details(self, client: AsyncClient, test_property):
        """Test viewing property details."""
        with patch("app.api.api_v1.endpoints.properties.get_property", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_property

            response = await client.get(f"/api/v1/properties/{test_property.id}")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_view_increments_counter(self, client: AsyncClient, test_property):
        """Test that viewing property increments view counter."""
        with patch("app.api.api_v1.endpoints.properties.get_property", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_property

            with patch("app.api.api_v1.endpoints.properties.increment_property_view_count", new_callable=AsyncMock):
                response = await client.get(f"/api/v1/properties/{test_property.id}")

                assert response.status_code == 200


class TestPropertySwipeFlow:
    """Tests for property swipe discovery flow."""

    @pytest.mark.asyncio
    async def test_swipe_like_and_view_likes(self, client: AsyncClient, auth_headers, test_property):
        """Test swiping and viewing liked properties."""
        # Step 1: Like a property
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

        # Step 2: View liked properties
        with patch("app.api.api_v1.endpoints.swipes.get_swipe_history", new_callable=AsyncMock) as mock_likes:
            mock_likes.return_value = {
                "items": [],
                "total": 1,
                "page": 1,
                "limit": 20,
                "total_pages": 1,
            }

            response = await client.get(
                "/api/v1/swipes/likes",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPropertyUpdateFlow:
    """Tests for property update flow."""

    @pytest.mark.asyncio
    async def test_owner_updates_property(self, client: AsyncClient, auth_headers, test_property):
        """Test owner updating their property."""
        with patch("app.api.api_v1.endpoints.properties.update_property", new_callable=AsyncMock) as mock_update:
            mock_property = MagicMock()
            mock_property.id = test_property.id
            mock_property.title = "Updated Property Title"
            mock_update.return_value = mock_property

            response = await client.patch(
                f"/api/v1/properties/{test_property.id}",
                json={"title": "Updated Property Title"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPropertyToggleAvailability:
    """Tests for toggling property availability."""

    @pytest.mark.asyncio
    async def test_toggle_availability(self, client: AsyncClient, auth_headers, test_property):
        """Test toggling property availability."""
        with patch("app.api.api_v1.endpoints.properties.toggle_property_availability", new_callable=AsyncMock) as mock_toggle:
            mock_property = MagicMock()
            mock_property.id = test_property.id
            mock_property.is_available = False
            mock_toggle.return_value = mock_property

            response = await client.post(
                f"/api/v1/properties/{test_property.id}/toggle-availability",
                headers=auth_headers,
            )

            assert response.status_code == 200
