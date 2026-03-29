"""
OAuth Token Store Service

Manages OAuth tokens, authorization codes, and sessions
using the centralized CacheManager for all storage operations.
"""

from __future__ import annotations

import time
from typing import Optional, Dict, Any

from app.core.cache import get_cache_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


class OAuthTokenStore:
    """OAuth token store delegating to the app-wide CacheManager.

    All storage operations (Redis / in-memory / null) are handled by
    CacheManager's backend selection and fallback chain.  This class
    only provides OAuth-specific key conventions and consume-on-read
    semantics for auth codes.
    """

    @staticmethod
    def _key(prefix: str, identifier: str) -> str:
        return f"oauth:{prefix}:{identifier}"

    # ------------------------------------------------------------------
    # Authorization Codes
    # ------------------------------------------------------------------

    async def store_auth_code(
        self,
        code: str,
        user_id: str,
        client_id: str,
        redirect_uri: Optional[str],
        scope: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        resource: Optional[str] = None,
        expires_in: int = 600,
    ) -> bool:
        try:
            cache = get_cache_manager()
            data = {
                "user_id": user_id,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "resource": resource,
                "created_at": time.time(),
                "expires_at": time.time() + expires_in,
            }
            await cache.set(self._key("auth_code", code), data, ttl=expires_in)
            logger.debug("Stored auth code", extra={"user_id": user_id, "client_id": client_id})
            return True
        except Exception as e:
            logger.error(f"Failed to store auth code: {e}")
            return False

    async def get_auth_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Retrieve and consume an authorization code (one-time use)."""
        try:
            cache = get_cache_manager()
            key = self._key("auth_code", code)
            data = await cache.get(key)
            if data is None:
                logger.debug("Auth code not found")
                return None
            # Consume: delete immediately after retrieval
            await cache.delete(key)
            # Check if expired (belt-and-suspenders for in-memory backend)
            if time.time() > data.get("expires_at", 0):
                logger.debug("Auth code expired")
                return None
            logger.debug("Auth code retrieved and consumed", extra={"user_id": data.get("user_id")})
            return data
        except Exception as e:
            logger.error(f"Failed to get auth code: {e}")
            return None

    async def delete_auth_code(self, code: str) -> bool:
        try:
            cache = get_cache_manager()
            await cache.delete(self._key("auth_code", code))
            return True
        except Exception as e:
            logger.error(f"Failed to delete auth code: {e}")
            return False

    # ------------------------------------------------------------------
    # Access & Refresh Tokens
    # ------------------------------------------------------------------

    async def store_oauth_tokens(
        self,
        access_token: str,
        refresh_token: str,
        user_id: str,
        scope: str,
        client_id: Optional[str] = None,
        resource: Optional[str] = None,
        access_token_expires_in: int = 3600,
        refresh_token_expires_in: int = 2592000,
    ) -> bool:
        try:
            cache = get_cache_manager()
            now = time.time()

            access_data = {
                "user_id": user_id,
                "scope": scope,
                "client_id": client_id,
                "resource": resource,
                "token_type": "Bearer",
                "created_at": now,
                "expires_at": now + access_token_expires_in,
                "refresh_token": refresh_token,
            }
            refresh_data = {
                "user_id": user_id,
                "scope": scope,
                "client_id": client_id,
                "resource": resource,
                "created_at": now,
                "expires_at": now + refresh_token_expires_in,
                "access_token": access_token,
            }

            await cache.set(self._key("access_token", access_token), access_data, ttl=access_token_expires_in)
            await cache.set(self._key("refresh_token", refresh_token), refresh_data, ttl=refresh_token_expires_in)

            # Store user's tokens for lookup
            user_tokens_key = self._key("user_tokens", user_id)
            existing: list = await cache.get(user_tokens_key) or []
            existing.append({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "client_id": client_id,
                "created_at": now,
            })
            await cache.set(user_tokens_key, existing, ttl=refresh_token_expires_in)

            logger.debug(f"Stored OAuth tokens for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens: {e}")
            return False

    async def get_access_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        try:
            cache = get_cache_manager()
            data = await cache.get(self._key("access_token", access_token))
            if data is None:
                logger.debug("Access token not found")
                return None
            # Belt-and-suspenders expiry check
            if time.time() > data.get("expires_at", 0):
                await cache.delete(self._key("access_token", access_token))
                logger.debug("Access token expired")
                return None
            logger.debug("Access token found", extra={"user_id": data.get("user_id")})
            return data
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    async def get_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        try:
            cache = get_cache_manager()
            data = await cache.get(self._key("refresh_token", refresh_token))
            if data is None:
                return None
            if time.time() > data.get("expires_at", 0):
                await cache.delete(self._key("refresh_token", refresh_token))
                return None
            return data
        except Exception as e:
            logger.error(f"Failed to get refresh token: {e}")
            return None

    async def revoke_token(self, token: str) -> bool:
        try:
            cache = get_cache_manager()
            await cache.delete(self._key("access_token", token))
            logger.debug("Revoked access token")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    async def delete_refresh_token(self, refresh_token: str) -> bool:
        try:
            cache = get_cache_manager()
            await cache.delete(self._key("refresh_token", refresh_token))
            return True
        except Exception as e:
            logger.error(f"Failed to delete refresh token: {e}")
            return False

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        try:
            refresh_data = await self.get_refresh_token(refresh_token)
            if refresh_data and refresh_data.get("access_token"):
                await self.revoke_token(refresh_data["access_token"])
            await self.delete_refresh_token(refresh_token)
            return True
        except Exception as e:
            logger.error(f"Failed to revoke refresh token: {e}")
            return False

    async def revoke_token_pair(
        self,
        *,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> bool:
        try:
            if refresh_token:
                refresh_data = await self.get_refresh_token(refresh_token)
                if refresh_data and refresh_data.get("access_token"):
                    await self.revoke_token(refresh_data["access_token"])
                await self.delete_refresh_token(refresh_token)

            if access_token:
                access_data = await self.get_access_token(access_token)
                if access_data and access_data.get("refresh_token"):
                    await self.delete_refresh_token(access_data["refresh_token"])
                await self.revoke_token(access_token)

            return True
        except Exception as e:
            logger.error(f"Failed to revoke token pair: {e}")
            return False

    # ------------------------------------------------------------------
    # OAuth Sessions
    # ------------------------------------------------------------------

    async def store_oauth_session(
        self,
        session_id: str,
        client_id: str,
        redirect_uri: Optional[str],
        scope: str,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        resource: Optional[str] = None,
        expires_in: int = 1800,
    ) -> bool:
        try:
            cache = get_cache_manager()
            data = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "resource": resource,
                "created_at": time.time(),
                "expires_at": time.time() + expires_in,
            }
            await cache.set(self._key("session", session_id), data, ttl=expires_in)
            return True
        except Exception as e:
            logger.error(f"Failed to store OAuth session: {e}")
            return False

    async def get_oauth_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            cache = get_cache_manager()
            data = await cache.get(self._key("session", session_id))
            if data is None:
                return None
            if time.time() > data.get("expires_at", 0):
                await cache.delete(self._key("session", session_id))
                return None
            return data
        except Exception as e:
            logger.error(f"Failed to get OAuth session: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        try:
            cache = get_cache_manager()
            await cache.delete(self._key("session", session_id))
            return True
        except Exception as e:
            logger.error(f"Failed to delete OAuth session: {e}")
            return False

    # ------------------------------------------------------------------
    # Dynamic Client Registration (RFC 7591)
    # ------------------------------------------------------------------

    async def store_client(
        self,
        client_id: str,
        metadata: Dict[str, Any],
        expires_in: Optional[int] = None,
    ) -> bool:
        try:
            cache = get_cache_manager()
            data = {
                **metadata,
                "client_id": client_id,
                "client_id_issued_at": int(time.time()),
            }
            if expires_in:
                data["expires_at"] = time.time() + expires_in
                await cache.set(self._key("client", client_id), data, ttl=expires_in)
            else:
                # No expiry — use a very long TTL (10 years) since CacheManager requires one
                await cache.set(self._key("client", client_id), data, ttl=315360000)
            logger.info(f"Stored OAuth client: {client_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store OAuth client: {e}")
            return False

    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        try:
            cache = get_cache_manager()
            data = await cache.get(self._key("client", client_id))
            if data is None:
                return None
            if "expires_at" in data and time.time() > data["expires_at"]:
                await cache.delete(self._key("client", client_id))
                return None
            # Sanitize optional string fields
            for field in ["client_uri", "logo_uri"]:
                if field in data and data[field] is None:
                    data[field] = ""
            return data
        except Exception as e:
            logger.error(f"Failed to get OAuth client: {e}")
            return None

    async def delete_client(self, client_id: str) -> bool:
        try:
            cache = get_cache_manager()
            await cache.delete(self._key("client", client_id))
            logger.info(f"Deleted OAuth client: {client_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete OAuth client: {e}")
            return False


# Global token store instance
oauth_token_store = OAuthTokenStore()
