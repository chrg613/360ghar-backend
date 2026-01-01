"""
Tests for user endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestGetCurrentUserEndpoint:
    """Tests for GET /api/v1/users/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """Test getting current user profile."""
        response = await client.get(
            "/api/v1/users/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data or "phone" in data

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting user profile without auth."""
        response = await client.get("/api/v1/users/me")

        assert response.status_code == 401


class TestUpdateUserEndpoint:
    """Tests for PATCH /api/v1/users/me endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_profile(self, client: AsyncClient, auth_headers):
        """Test updating user profile."""
        with patch("app.api.api_v1.endpoints.users.update_user", new_callable=AsyncMock) as mock_update:
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.full_name = "Updated Name"
            mock_update.return_value = mock_user

            response = await client.patch(
                "/api/v1/users/me",
                json={"full_name": "Updated Name"},
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_user_email(self, client: AsyncClient, auth_headers):
        """Test updating user email."""
        with patch("app.api.api_v1.endpoints.users.update_user", new_callable=AsyncMock) as mock_update:
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "newemail@example.com"
            mock_update.return_value = mock_user

            response = await client.patch(
                "/api/v1/users/me",
                json={"email": "newemail@example.com"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestGetUserPropertiesEndpoint:
    """Tests for GET /api/v1/users/me/properties endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_properties(self, client: AsyncClient, auth_headers):
        """Test getting user's properties."""
        with patch("app.api.api_v1.endpoints.users.list_user_properties", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            response = await client.get(
                "/api/v1/users/me/properties",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestGetUserBookingsEndpoint:
    """Tests for GET /api/v1/users/me/bookings endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_bookings(self, client: AsyncClient, auth_headers):
        """Test getting user's bookings."""
        with patch("app.api.api_v1.endpoints.users.get_user_bookings", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"bookings": [], "total": 0}

            response = await client.get(
                "/api/v1/users/me/bookings",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestGetUserVisitsEndpoint:
    """Tests for GET /api/v1/users/me/visits endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_visits(self, client: AsyncClient, auth_headers):
        """Test getting user's visits."""
        with patch("app.api.api_v1.endpoints.users.get_user_visits", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"visits": [], "total": 0}

            response = await client.get(
                "/api/v1/users/me/visits",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestDeleteUserEndpoint:
    """Tests for DELETE /api/v1/users/me endpoint."""

    @pytest.mark.asyncio
    async def test_delete_user_account(self, client: AsyncClient, auth_headers):
        """Test deleting user account."""
        with patch("app.api.api_v1.endpoints.users.delete_user", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            response = await client.delete(
                "/api/v1/users/me",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestUserPreferencesEndpoint:
    """Tests for user preferences endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_preferences(self, client: AsyncClient, auth_headers):
        """Test getting user preferences."""
        with patch("app.api.api_v1.endpoints.users.get_user_preferences", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"notifications_enabled": True}

            response = await client.get(
                "/api/v1/users/me/preferences",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_user_preferences(self, client: AsyncClient, auth_headers):
        """Test updating user preferences."""
        with patch("app.api.api_v1.endpoints.users.update_user_preferences", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {"notifications_enabled": False}

            response = await client.patch(
                "/api/v1/users/me/preferences",
                json={"notifications_enabled": False},
                headers=auth_headers,
            )

            assert response.status_code == 200
