"""
Tests for OAuth endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestOAuthAuthorizeEndpoint:
    """Tests for GET /mcp/oauth/authorize endpoint."""

    @pytest.mark.asyncio
    async def test_authorize_success(self, client: AsyncClient):
        """Test OAuth authorize redirect."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.store_oauth_session = AsyncMock()

            response = await client.get(
                "/mcp/oauth/authorize",
                params={
                    "response_type": "code",
                    "client_id": "ghar360-mcp",
                    "redirect_uri": "http://localhost:3000/callback",
                    "scope": "mcp:read mcp:write",
                    "state": "test_state",
                },
                follow_redirects=False,
            )

            # Should redirect to consent page
            assert response.status_code in [302, 307]

    @pytest.mark.asyncio
    async def test_authorize_invalid_response_type(self, client: AsyncClient):
        """Test authorize with invalid response type."""
        response = await client.get(
            "/mcp/oauth/authorize",
            params={
                "response_type": "token",  # Only "code" is supported
                "client_id": "ghar360-mcp",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_authorize_invalid_client_id(self, client: AsyncClient):
        """Test authorize with invalid client ID."""
        response = await client.get(
            "/mcp/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "invalid_client",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_authorize_with_pkce(self, client: AsyncClient):
        """Test authorize with PKCE challenge."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.store_oauth_session = AsyncMock()

            response = await client.get(
                "/mcp/oauth/authorize",
                params={
                    "response_type": "code",
                    "client_id": "ghar360-mcp",
                    "code_challenge": "test_challenge",
                    "code_challenge_method": "S256",
                },
                follow_redirects=False,
            )

            assert response.status_code in [302, 307]


class TestOAuthConsentEndpoint:
    """Tests for /mcp/oauth/consent endpoint."""

    @pytest.mark.asyncio
    async def test_consent_page(self, client: AsyncClient):
        """Test consent page display."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_oauth_session = AsyncMock(return_value={
                "client_id": "ghar360-mcp",
                "scope": "mcp:read mcp:write",
                "state": "test_state",
            })

            response = await client.get(
                "/mcp/oauth/consent",
                params={"session": "test_session"},
            )

            assert response.status_code == 200
            assert "360Ghar" in response.text

    @pytest.mark.asyncio
    async def test_consent_invalid_session(self, client: AsyncClient):
        """Test consent with invalid session."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_oauth_session = AsyncMock(return_value=None)

            response = await client.get(
                "/mcp/oauth/consent",
                params={"session": "invalid_session"},
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_process_consent_success(self, client: AsyncClient):
        """Test processing consent form."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_oauth_session = AsyncMock(return_value={
                "client_id": "ghar360-mcp",
                "redirect_uri": "http://localhost:3000/callback",
                "scope": "mcp:read mcp:write",
                "state": "test_state",
                "code_challenge": None,
                "code_challenge_method": None,
            })
            mock_store.store_auth_code = AsyncMock()
            mock_store.delete_session = AsyncMock()

            with patch("app.api.api_v1.endpoints.oauth.get_supabase_auth_client") as mock_supabase:
                mock_auth = MagicMock()
                mock_session = MagicMock()
                mock_session.access_token = "test_token"
                mock_auth.auth.sign_in_with_password.return_value = MagicMock(session=mock_session)
                mock_supabase.return_value = mock_auth

                with patch("app.api.api_v1.endpoints.oauth.verify_supabase_token", new_callable=AsyncMock) as mock_verify:
                    mock_verify.return_value = {"id": "user_123", "phone": "+919876543210"}

                    with patch("app.api.api_v1.endpoints.oauth.get_or_create_user_from_supabase", new_callable=AsyncMock) as mock_get_user:
                        mock_user = MagicMock()
                        mock_user.id = 1
                        mock_get_user.return_value = mock_user

                        response = await client.post(
                            "/mcp/oauth/consent",
                            data={
                                "phone": "+919876543210",
                                "password": "test_password",
                                "session": "test_session",
                                "action": "authorize",
                            },
                            follow_redirects=False,
                        )

                        # Should redirect with auth code
                        assert response.status_code in [302, 307, 200]


class TestOAuthTokenEndpoint:
    """Tests for POST /mcp/oauth/token endpoint."""

    @pytest.mark.asyncio
    async def test_token_authorization_code_grant(self, client: AsyncClient):
        """Test token exchange with authorization code."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_auth_code = AsyncMock(return_value={
                "user_id": "1",
                "client_id": "ghar360-mcp",
                "redirect_uri": "http://localhost:3000/callback",
                "scope": "mcp:read mcp:write",
                "code_challenge": None,
            })
            mock_store.store_oauth_tokens = AsyncMock()

            response = await client.post(
                "/mcp/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": "test_auth_code",
                    "client_id": "ghar360-mcp",
                    "redirect_uri": "http://localhost:3000/callback",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_token_missing_code(self, client: AsyncClient):
        """Test token exchange without authorization code."""
        response = await client.post(
            "/mcp/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "ghar360-mcp",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_token_invalid_code(self, client: AsyncClient):
        """Test token exchange with invalid authorization code."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_auth_code = AsyncMock(return_value=None)

            response = await client.post(
                "/mcp/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": "invalid_code",
                    "client_id": "ghar360-mcp",
                },
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_token_refresh_grant(self, client: AsyncClient):
        """Test token refresh."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_refresh_token = AsyncMock(return_value={
                "user_id": "1",
                "scope": "mcp:read mcp:write",
            })
            mock_store.store_oauth_tokens = AsyncMock()

            response = await client.post(
                "/mcp/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": "test_refresh_token",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    @pytest.mark.asyncio
    async def test_token_invalid_refresh_token(self, client: AsyncClient):
        """Test token refresh with invalid refresh token."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_refresh_token = AsyncMock(return_value=None)

            response = await client.post(
                "/mcp/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": "invalid_token",
                },
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_token_unsupported_grant_type(self, client: AsyncClient):
        """Test token with unsupported grant type."""
        response = await client.post(
            "/mcp/oauth/token",
            data={
                "grant_type": "client_credentials",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_token_with_pkce_verification(self, client: AsyncClient):
        """Test token exchange with PKCE verification."""
        with patch("app.api.api_v1.endpoints.oauth.oauth_token_store") as mock_store:
            mock_store.get_auth_code = AsyncMock(return_value={
                "user_id": "1",
                "client_id": "ghar360-mcp",
                "scope": "mcp:read mcp:write",
                "code_challenge": "test_challenge",
                "code_challenge_method": "plain",
            })
            mock_store.store_oauth_tokens = AsyncMock()

            response = await client.post(
                "/mcp/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": "test_auth_code",
                    "client_id": "ghar360-mcp",
                    "code_verifier": "test_challenge",  # Plain method
                },
            )

            assert response.status_code == 200


class TestOAuthMetadataEndpoint:
    """Tests for OAuth well-known metadata endpoint."""

    @pytest.mark.asyncio
    async def test_authorization_server_metadata(self, client: AsyncClient):
        """Test OAuth authorization server metadata."""
        response = await client.get("/.well-known/oauth-authorization-server/mcp/oauth")

        assert response.status_code == 200
        data = response.json()
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "response_types_supported" in data
        assert "code" in data["response_types_supported"]


class TestPKCEVerification:
    """Tests for PKCE verification logic."""

    def test_verify_pkce_s256(self):
        """Test PKCE S256 verification."""
        from app.api.api_v1.endpoints.oauth import verify_pkce
        import base64
        import hashlib

        # Generate valid PKCE pair
        verifier = "test_verifier_12345"
        hash_obj = hashlib.sha256(verifier.encode('ascii')).digest()
        challenge = base64.urlsafe_b64encode(hash_obj).decode('ascii').rstrip('=')

        assert verify_pkce(challenge, verifier, "S256") is True
        assert verify_pkce(challenge, "wrong_verifier", "S256") is False

    def test_verify_pkce_plain(self):
        """Test PKCE plain verification."""
        from app.api.api_v1.endpoints.oauth import verify_pkce

        challenge = "test_challenge"
        verifier = "test_challenge"

        assert verify_pkce(challenge, verifier, "plain") is True
        assert verify_pkce(challenge, "wrong", "plain") is False

    def test_verify_pkce_missing_values(self):
        """Test PKCE with missing values."""
        from app.api.api_v1.endpoints.oauth import verify_pkce

        assert verify_pkce(None, "verifier", "S256") is False
        assert verify_pkce("challenge", None, "S256") is False
        assert verify_pkce(None, None, "S256") is False
