"""
End-to-end tests for user registration flow.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestUserRegistrationFlow:
    """Tests for complete user registration flow."""

    @pytest.mark.asyncio
    async def test_full_registration_flow(self, client: AsyncClient):
        """Test complete user registration from start to finish."""
        # Step 1: Register new user
        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            user_id = str(uuid.uuid4())
            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.phone = "+919876543210"
            mock_user.email = "newuser@example.com"
            mock_user.user_metadata = {"full_name": "New User"}

            mock_session = MagicMock()
            mock_session.access_token = "new_access_token"

            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_response.session = mock_session

            mock_supabase = MagicMock()
            mock_supabase.auth.sign_up.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch(
                    "app.api.api_v1.endpoints.auth.get_or_create_user_from_supabase",
                    new_callable=AsyncMock,
                ) as mock_create:
                    mock_db_user = MagicMock()
                    mock_db_user.id = 1
                    mock_db_user.phone = "+919876543210"
                    mock_db_user.email = "newuser@example.com"
                    mock_create.return_value = mock_db_user

                    response = await client.post(
                        "/api/v1/auth/register/",
                        json={
                            "phone": "+919876543210",
                            "password": "SecurePass123!",
                            "full_name": "New User",
                            "email": "newuser@example.com",
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "access_token" in data
                    assert data["message"] == "User registered successfully"

    @pytest.mark.asyncio
    async def test_registration_then_login_flow(self, client: AsyncClient):
        """Test user can login after registration."""
        user_id = str(uuid.uuid4())
        phone = "+919876543210"

        # Mock for login
        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_session = MagicMock()
            mock_session.access_token = "login_access_token"

            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.phone = phone
            mock_user.email_confirmed_at = "2024-01-01T00:00:00Z"
            mock_user.user_metadata = {}

            mock_response = MagicMock()
            mock_response.session = mock_session
            mock_response.user = mock_user

            mock_supabase = MagicMock()
            mock_supabase.auth.sign_in_with_password.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch(
                    "app.api.api_v1.endpoints.auth.verify_supabase_token",
                    new_callable=AsyncMock,
                ) as mock_verify:
                    mock_verify.return_value = {
                        "id": user_id,
                        "phone": phone,
                        "email_verified": True,
                    }

                    with patch(
                        "app.api.api_v1.endpoints.auth.get_or_create_user_from_supabase",
                        new_callable=AsyncMock,
                    ) as mock_create:
                        mock_db_user = MagicMock()
                        mock_db_user.id = 1
                        mock_create.return_value = mock_db_user

                        response = await client.post(
                            "/api/v1/auth/login/",
                            json={
                                "phone": phone,
                                "password": "SecurePass123!",
                            },
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert "access_token" in data
                        assert data["token_type"] == "bearer"


class TestOTPRegistrationFlow:
    """Tests for OTP-based registration flow."""

    @pytest.mark.asyncio
    async def test_otp_request_and_verify_flow(self, client: AsyncClient):
        """Test OTP request followed by verification."""
        phone = "+919876543210"

        # Step 1: Request OTP
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

                    assert response.status_code == 200
                    assert response.json()["message"] == "OTP sent"

        # Step 2: Verify OTP
        user_id = str(uuid.uuid4())

        with patch("app.api.api_v1.endpoints.auth.get_supabase_auth_client") as mock_client:
            mock_session = MagicMock()
            mock_session.access_token = "verified_token"

            mock_response = MagicMock()
            mock_response.session = mock_session

            mock_supabase = MagicMock()
            mock_supabase.auth.verify_otp.return_value = mock_response
            mock_client.return_value = mock_supabase

            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = mock_response

                with patch(
                    "app.api.api_v1.endpoints.auth.verify_supabase_token",
                    new_callable=AsyncMock,
                ) as mock_verify:
                    mock_verify.return_value = {
                        "id": user_id,
                        "phone": phone,
                        "email_verified": True,
                    }

                    with patch(
                        "app.api.api_v1.endpoints.auth.get_or_create_user_from_supabase",
                        new_callable=AsyncMock,
                    ) as mock_create:
                        mock_db_user = MagicMock()
                        mock_db_user.id = 1
                        mock_create.return_value = mock_db_user

                        response = await client.post(
                            "/api/v1/auth/otp/verify",
                            json={
                                "phone": phone,
                                "token": "123456",
                                "type": "sms",
                            },
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert "access_token" in data


class TestRegistrationValidation:
    """Tests for registration input validation."""

    @pytest.mark.asyncio
    async def test_registration_requires_phone(self, client: AsyncClient):
        """Test registration requires phone number."""
        response = await client.post(
            "/api/v1/auth/register/",
            json={
                "password": "password123",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_registration_requires_password(self, client: AsyncClient):
        """Test registration requires password."""
        response = await client.post(
            "/api/v1/auth/register/",
            json={
                "phone": "+919876543210",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422
