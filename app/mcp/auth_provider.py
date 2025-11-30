from __future__ import annotations

import time
from typing import Optional

import fastmcp
from fastmcp.server.auth import AccessToken, RemoteAuthProvider, TokenVerifier

from app.core.auth import verify_supabase_token
from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class SupabaseTokenVerifier(TokenVerifier):
    """
    Token verifier that validates both Supabase JWT access tokens and
    first‑party OAuth access tokens issued by this backend.

    It returns a FastMCP `AccessToken` with rich `claims` that downstream
    MCP tools can use to resolve the current user.
    """

    def __init__(self, required_scopes: Optional[list[str]] | None = None):
        super().__init__(base_url=None, required_scopes=required_scopes)

    async def verify_token(self, token: str) -> AccessToken | None:
        """
        Verify the provided bearer token.

        Order of checks:
        1. Try Supabase JWT (backward compatibility for existing clients)
        2. Try first‑party OAuth access token from our token store
        """
        scopes = self.required_scopes or ["mcp:read", "mcp:write"]

        # 1) Supabase JWT (backward compatible path)
        try:
            supa = await verify_supabase_token(token)
            if supa:
                user_id = supa.get("id")
                if user_id:
                    claims = {
                        "sub": user_id,
                        "email": supa.get("email"),
                        "phone": supa.get("phone"),
                        "email_verified": supa.get("email_verified", False),
                        "user_metadata": supa.get("user_metadata") or {},
                        "auth_method": "supabase_jwt",
                    }

                    return AccessToken(
                        token=token,
                        client_id="supabase",
                        scopes=scopes,
                        expires_at=None,
                        resource=None,
                        claims=claims,
                    )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Supabase token verification failed, trying OAuth: %s", exc)

        # 2) First‑party OAuth access token
        try:
            # Heuristic: our OAuth access tokens are long, random strings without dots
            if len(token) > 40 and "." not in token:
                from app.services.oauth_token_store import oauth_token_store

                token_data = await oauth_token_store.get_access_token(token)
                if token_data:
                    user_id = token_data["user_id"]
                    expires_at_raw = token_data.get("expires_at")
                    expires_at = int(expires_at_raw) if expires_at_raw else None

                    claims = {
                        "sub": user_id,
                        "auth_method": "oauth",
                        "scope": token_data.get("scope", "mcp:read mcp:write"),
                    }

                    if "email" in token_data:
                        claims["email"] = token_data["email"]
                    if "phone" in token_data:
                        claims["phone"] = token_data["phone"]

                    logger.debug("OAuth token verified for user %s", user_id)

                    return AccessToken(
                        token=token,
                        client_id="ghar360-mcp",
                        scopes=claims["scope"].split(),
                        expires_at=expires_at,
                        resource=None,
                        claims=claims,
                    )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error verifying OAuth token for MCP: %s", exc)

        return None


class SupabaseAuthProvider(RemoteAuthProvider):
    """
    RemoteAuthProvider that supports both Supabase JWT and first‑party OAuth
    access tokens for the MCP HTTP endpoint.

    It exposes protected resource metadata for the MCP `/mcp` endpoint and
    advertises the backend's OAuth authorization server located under
    `/mcp/oauth/*`.
    """

    def __init__(self) -> None:
        """
        Initialize the auth provider using backend configuration.

        FastMCP may instantiate this class without arguments based on the
        `FASTMCP_SERVER_AUTH` setting. We derive the public base URL from
        configuration so that MCP HTTP auth works in both local and production
        environments.
        """
        # Determine the public base URL (scheme + host, optionally port)
        public_base_url = getattr(settings, "PUBLIC_BASE_URL", None)
        if not public_base_url:
            if settings.ENVIRONMENT == "production":
                public_base_url = "https://api.360ghar.com"
            else:
                public_base_url = "http://localhost:8000"

        # Resource server base URL (used to build the protected `/mcp` URL)
        resource_base_url = public_base_url

        # OAuth authorization server issuer URL (path-aware as per RFC 8414)
        # This will result in metadata being discovered at:
        #   {scheme}://{host}/.well-known/oauth-authorization-server/mcp/oauth
        auth_server_url = f"{public_base_url}/mcp/oauth"

        # Initialize token verifier with required scopes for MCP access
        required_scopes = ["mcp:read", "mcp:write"]
        token_verifier = SupabaseTokenVerifier(required_scopes=required_scopes)

        super().__init__(
            token_verifier=token_verifier,
            authorization_servers=[auth_server_url],
            base_url=resource_base_url,
            resource_name="360Ghar MCP API",
            resource_documentation=f"{public_base_url}/docs",
        )


def configure_fastmcp_auth() -> None:
    """
    Configure the global FastMCP `server_auth` setting so that any FastMCP
    server created in this process automatically uses SupabaseAuthProvider
    for HTTP auth.

    This is designed to be called exactly once on startup.
    """
    if fastmcp.settings.server_auth is None:
        fastmcp.settings.server_auth = "app.mcp.auth_provider.SupabaseAuthProvider"
