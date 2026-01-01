"""
Tests for authentication API endpoints.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login/."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, mock_supabase_auth_client):
        """Test successful login returns token and user."""
        user_id = str(uuid.uuid4())

        # Mock successful auth response
        mock_session = MagicMock()
        mock_session.access_token = "mock_access_token"
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.phone = "+919876543210"
        mock_user.email = "test@example.com"
        mock_user.email_confirmed_at = "2024-01-01T00:00:00Z"
        mock_user.user_metadata = {"full_name": "Test User"}

        mock_response = MagicMock()
        mock_response.session = mock_session
        mock_response.user = mock_user

        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_supabase.auth.sign_in_with_password.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch("app.api.api_v1.endpoints.auth.verify_supabase_token", new_callable=AsyncMock) as mock_verify:
                    mock_verify.return_value = {
                        "id": user_id,
                        "email": "test@example.com",
                        "phone": "+919876543210",
                        "email_verified": True,
                        "user_metadata": {"full_name": "Test User"},
                    }

                    with patch("app.api.api_v1.endpoints.auth.get_or_create_user_from_supabase", new_callable=AsyncMock) as mock_user_create:
                        mock_db_user = MagicMock()
                        mock_db_user.id = 1
                        mock_db_user.email = "test@example.com"
                        mock_user_create.return_value = mock_db_user

                        response = await client.post(
                            "/api/v1/auth/login/",
                            json={"phone": "+919876543210", "password": "password123"},
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert "access_token" in data
                        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, client: AsyncClient):
        """Test login returns 404 when user doesn't exist."""
        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_response = MagicMock()
            mock_response.session = None
            mock_supabase.auth.sign_in_with_password.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch("app.api.api_v1.endpoints.auth.admin_find_user_by_phone", new_callable=AsyncMock) as mock_admin:
                    mock_admin.return_value = None

                    response = await client.post(
                        "/api/v1/auth/login/",
                        json={"phone": "+919999999999", "password": "wrongpass"},
                    )

                    assert response.status_code == 404
                    data = response.json()
                    assert data["detail"]["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login returns 401 for invalid password."""
        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_response = MagicMock()
            mock_response.session = None
            mock_supabase.auth.sign_in_with_password.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch("app.api.api_v1.endpoints.auth.admin_find_user_by_phone", new_callable=AsyncMock) as mock_admin:
                    mock_admin.return_value = {"id": str(uuid.uuid4()), "phone": "+919876543210"}

                    response = await client.post(
                        "/api/v1/auth/login/",
                        json={"phone": "+919876543210", "password": "wrongpass"},
                    )

                    assert response.status_code == 401
                    data = response.json()
                    assert data["detail"]["code"] == "INVALID_CREDENTIALS"


class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register/."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful registration."""
        user_id = str(uuid.uuid4())

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.phone = "+919876543210"
        mock_user.email = "new@example.com"
        mock_user.user_metadata = {"full_name": "New User"}

        mock_session = MagicMock()
        mock_session.access_token = "new_access_token"

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_supabase.auth.sign_up.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch("app.api.api_v1.endpoints.auth.get_or_create_user_from_supabase", new_callable=AsyncMock) as mock_user_create:
                    mock_db_user = MagicMock()
                    mock_db_user.id = 1
                    mock_user_create.return_value = mock_db_user

                    response = await client.post(
                        "/api/v1/auth/register/",
                        json={
                            "phone": "+919876543210",
                            "password": "password123",
                            "full_name": "New User",
                            "email": "new@example.com",
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["message"] == "User registered successfully"
                    assert "access_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_phone(self, client: AsyncClient):
        """Test registration fails for duplicate phone."""
        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_supabase.auth.sign_up.side_effect = Exception("User already exists")
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.side_effect = Exception("User already exists")

                response = await client.post(
                    "/api/v1/auth/register/",
                    json={
                        "phone": "+919876543210",
                        "password": "password123",
                        "full_name": "New User",
                    },
                )

                assert response.status_code == 409
                data = response.json()
                assert data["detail"]["code"] == "USER_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration fails for weak password."""
        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_supabase.auth.sign_up.side_effect = Exception("Password too short")
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.side_effect = Exception("Password too short")

                response = await client.post(
                    "/api/v1/auth/register/",
                    json={
                        "phone": "+919876543210",
                        "password": "123",
                        "full_name": "New User",
                    },
                )

                assert response.status_code == 400
                data = response.json()
                assert data["detail"]["code"] == "WEAK_PASSWORD"


class TestOTPRequestEndpoint:
    """Tests for POST /api/v1/auth/otp/request."""

    @pytest.mark.asyncio
    async def test_otp_request_success(self, client: AsyncClient, mock_cache_manager):
        """Test successful OTP request."""
        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_supabase.auth.sign_in_with_otp.return_value = None
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = None

                with patch("app.api.api_v1.endpoints.auth.get_cache_manager") as mock_cache:
                    mock_manager = MagicMock()
                    mock_manager.is_available.return_value = False
                    mock_cache.return_value = mock_manager

                    response = await client.post(
                        "/api/v1/auth/otp/request",
                        json={"phone": "+919876543210"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["message"] == "OTP sent"

    @pytest.mark.asyncio
    async def test_otp_request_invalid_phone_format(self, client: AsyncClient):
        """Test OTP request fails for invalid phone format."""
        response = await client.post(
            "/api/v1/auth/otp/request",
            json={"phone": "123456"},  # Invalid format
        )

        assert response.status_code == 422


class TestOTPVerifyEndpoint:
    """Tests for POST /api/v1/auth/otp/verify."""

    @pytest.mark.asyncio
    async def test_otp_verify_success(self, client: AsyncClient):
        """Test successful OTP verification."""
        user_id = str(uuid.uuid4())

        mock_session = MagicMock()
        mock_session.access_token = "verified_token"

        mock_response = MagicMock()
        mock_response.session = mock_session

        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_supabase.auth.verify_otp.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch("app.api.api_v1.endpoints.auth.verify_supabase_token", new_callable=AsyncMock) as mock_verify:
                    mock_verify.return_value = {
                        "id": user_id,
                        "phone": "+919876543210",
                        "email_verified": True,
                    }

                    with patch("app.api.api_v1.endpoints.auth.get_or_create_user_from_supabase", new_callable=AsyncMock) as mock_user_create:
                        mock_db_user = MagicMock()
                        mock_db_user.id = 1
                        mock_user_create.return_value = mock_db_user

                        response = await client.post(
                            "/api/v1/auth/otp/verify",
                            json={
                                "phone": "+919876543210",
                                "token": "123456",
                                "type": "sms",
                            },
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert "access_token" in data
                        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_otp_verify_invalid_otp(self, client: AsyncClient):
        """Test OTP verification fails for invalid OTP."""
        mock_response = MagicMock()
        mock_response.session = None

        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_supabase = MagicMock()
            mock_supabase.auth.verify_otp.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                response = await client.post(
                    "/api/v1/auth/otp/verify",
                    json={
                        "phone": "+919876543210",
                        "token": "000000",
                        "type": "sms",
                    },
                )

                assert response.status_code == 401
                data = response.json()
                assert data["detail"]["code"] == "OTP_INVALID"


class TestPhoneValidation:
    """Tests for phone number validation."""

    @pytest.mark.asyncio
    async def test_valid_e164_phone(self, client: AsyncClient):
        """Test valid E.164 phone formats are accepted."""
        valid_phones = [
            "+919876543210",
            "+14155552671",
            "+447911123456",
        ]

        for phone in valid_phones:
            with patch("app.api.api_v1.endpoints.auth.get_cache_manager") as mock_cache:
                mock_manager = MagicMock()
                mock_manager.is_available.return_value = False
                mock_cache.return_value = mock_manager

                with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
                    mock_supabase = MagicMock()
                    mock_supabase.auth.sign_in_with_otp.return_value = None
                    mock_client.return_value = mock_supabase

                    with patch("anyio.to_thread.run_sync", new_callable=AsyncMock):
                        response = await client.post(
                            "/api/v1/auth/otp/request",
                            json={"phone": phone},
                        )
                        # Should not fail validation
                        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_invalid_phone_formats_rejected(self, client: AsyncClient):
        """Test invalid phone formats are rejected."""
        invalid_phones = [
            "9876543210",  # Missing +
            "+91",  # Too short
            "abc123",  # Contains letters
        ]

        for phone in invalid_phones:
            response = await client.post(
                "/api/v1/auth/otp/request",
                json={"phone": phone},
            )
            assert response.status_code == 422
