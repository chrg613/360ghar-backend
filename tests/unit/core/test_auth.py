"""
Tests for app.core.auth module.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx


class TestGetSupabaseClients:
    """Tests for Supabase client creation functions."""

    def test_get_supabase_auth_client_creates_singleton(self):
        """Test auth client is created as singleton."""
        with patch("app.core.auth.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            # Reset global
            import app.core.auth as auth_module
            auth_module._supabase_client = None

            client1 = auth_module.get_supabase_auth_client()
            client2 = auth_module.get_supabase_auth_client()

            # Should only create once
            assert mock_create.call_count == 1
            assert client1 is client2

    def test_get_supabase_service_client_creates_singleton(self):
        """Test service client is created as singleton."""
        with patch("app.core.auth.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            import app.core.auth as auth_module
            auth_module._supabase_service_client = None

            client1 = auth_module.get_supabase_service_client()
            client2 = auth_module.get_supabase_service_client()

            assert mock_create.call_count == 1
            assert client1 is client2


class TestVerifySupabaseToken:
    """Tests for verify_supabase_token function."""

    @pytest.mark.asyncio
    async def test_verify_token_success(self):
        """Test successful token verification."""
        mock_user = MagicMock()
        mock_user.id = str(uuid.uuid4())
        mock_user.email = "test@example.com"
        mock_user.phone = "+919876543210"
        mock_user.email_confirmed_at = "2024-01-01T00:00:00Z"
        mock_user.user_metadata = {"full_name": "Test User"}

        mock_response = MagicMock()
        mock_response.user = mock_user

        with patch("app.core.auth.get_supabase_auth_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.auth.get_user.return_value = mock_response
            mock_get_client.return_value = mock_client

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                from app.core.auth import verify_supabase_token

                result = await verify_supabase_token("valid_token")

                assert result is not None
                assert result["id"] == mock_user.id
                assert result["email"] == mock_user.email
                assert result["phone"] == mock_user.phone
                assert result["email_verified"] is True

    @pytest.mark.asyncio
    async def test_verify_token_no_user(self):
        """Test token verification when no user returned."""
        mock_response = MagicMock()
        mock_response.user = None

        with patch("app.core.auth.get_supabase_auth_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                from app.core.auth import verify_supabase_token

                result = await verify_supabase_token("invalid_token")

                assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_exception(self):
        """Test token verification handles exceptions."""
        with patch("app.core.auth.get_supabase_auth_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.side_effect = Exception("Auth error")

                from app.core.auth import verify_supabase_token

                result = await verify_supabase_token("any_token")

                assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_phone_confirmed(self):
        """Test token verification with phone confirmation."""
        mock_user = MagicMock()
        mock_user.id = str(uuid.uuid4())
        mock_user.email = None
        mock_user.phone = "+919876543210"
        mock_user.email_confirmed_at = None
        mock_user.phone_confirmed_at = "2024-01-01T00:00:00Z"
        mock_user.user_metadata = {}

        mock_response = MagicMock()
        mock_response.user = mock_user

        with patch("app.core.auth.get_supabase_auth_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                from app.core.auth import verify_supabase_token

                result = await verify_supabase_token("valid_token")

                assert result is not None
                assert result["email_verified"] is True


class TestAdminFindUserByPhone:
    """Tests for admin_find_user_by_phone function."""

    @pytest.mark.asyncio
    async def test_find_user_success(self):
        """Test successful user lookup by phone."""
        user_id = str(uuid.uuid4())
        phone = "+919876543210"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "users": [{
                    "id": user_id,
                    "email": "test@example.com",
                    "phone": phone,
                    "user_metadata": {"name": "Test"},
                }]
            }

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from app.core.auth import admin_find_user_by_phone

            result = await admin_find_user_by_phone(phone)

            assert result is not None
            assert result["id"] == user_id
            assert result["phone"] == phone

    @pytest.mark.asyncio
    async def test_find_user_not_found(self):
        """Test user lookup when user not found."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"users": []}

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from app.core.auth import admin_find_user_by_phone

            result = await admin_find_user_by_phone("+919999999999")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_user_404_response(self):
        """Test user lookup with 404 response."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 404

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from app.core.auth import admin_find_user_by_phone

            result = await admin_find_user_by_phone("+919876543210")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_user_phone_mismatch(self):
        """Test user lookup when phone doesn't match."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "users": [{
                    "id": str(uuid.uuid4()),
                    "phone": "+919999999999",  # Different phone
                }]
            }

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from app.core.auth import admin_find_user_by_phone

            result = await admin_find_user_by_phone("+919876543210")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_user_exception(self):
        """Test user lookup handles exceptions."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from app.core.auth import admin_find_user_by_phone

            result = await admin_find_user_by_phone("+919876543210")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_user_list_response(self):
        """Test user lookup with list response format."""
        user_id = str(uuid.uuid4())
        phone = "+919876543210"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Some GoTrue versions return list directly
            mock_response.json.return_value = [{
                "id": user_id,
                "email": "test@example.com",
                "phone": phone,
                "user_metadata": {},
            }]

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            from app.core.auth import admin_find_user_by_phone

            result = await admin_find_user_by_phone(phone)

            assert result is not None
            assert result["id"] == user_id
