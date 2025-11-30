"""
OAuth Token Store Service

This service manages OAuth tokens, authorization codes, and sessions.
It provides both in-memory (for development) and Redis-based storage.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OAuthTokenStore:
    """
    OAuth token store with both in-memory and Redis backends.
    """
    
    def __init__(self):
        self._redis_client = None
        self._in_memory_store: Dict[str, Dict[str, Any]] = {}
        self.use_redis = False
        
        # Try to initialize Redis if available
        try:
            import redis
            self._redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            self._redis_client.ping()
            self.use_redis = True
            logger.info("OAuth token store initialized with Redis backend")
        except Exception as e:
            logger.warning(f"Redis not available for OAuth token store, using in-memory storage: {e}")
            self.use_redis = False
    
    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create a consistent key for storage"""
        return f"oauth:{prefix}:{identifier}"
    
    def _serialize_data(self, data: Dict[str, Any]) -> str:
        """Serialize data for storage"""
        return json.dumps(data)
    
    def _deserialize_data(self, data: str) -> Dict[str, Any]:
        """Deserialize data from storage"""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}
    
    async def store_auth_code(
        self, 
        code: str, 
        user_id: str,
        client_id: str,
        redirect_uri: Optional[str],
        scope: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        expires_in: int = 600  # 10 minutes
    ) -> bool:
        """Store authorization code"""
        try:
            auth_data = {
                "user_id": user_id,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "created_at": time.time(),
                "expires_at": time.time() + expires_in
            }
            
            if self.use_redis:
                key = self._make_key("auth_code", code)
                # Redis client here is synchronous; use it directly
                self._redis_client.setex(
                    key,
                    expires_in,
                    self._serialize_data(auth_data),
                )
            else:
                # In-memory storage
                self._in_memory_store[f"auth_code:{code}"] = auth_data
            
            logger.debug(f"Stored auth code for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store auth code: {e}")
            return False
    
    async def get_auth_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Retrieve and consume authorization code"""
        try:
            if self.use_redis:
                key = self._make_key("auth_code", code)
                data = self._redis_client.get(key)
                if data:
                    # Delete the code after retrieval (one-time use)
                    self._redis_client.delete(key)
                    return self._deserialize_data(data)
            else:
                # In-memory storage
                key = f"auth_code:{code}"
                if key in self._in_memory_store:
                    auth_data = self._in_memory_store[key]
                    # Check expiration
                    if time.time() > auth_data.get("expires_at", 0):
                        del self._in_memory_store[key]
                        return None
                    # Delete the code after retrieval
                    del self._in_memory_store[key]
                    return auth_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get auth code: {e}")
            return None
    
    async def store_oauth_tokens(
        self,
        access_token: str,
        refresh_token: str,
        user_id: str,
        scope: str,
        access_token_expires_in: int = 3600,
        refresh_token_expires_in: int = 2592000  # 30 days
    ) -> bool:
        """Store OAuth access and refresh tokens"""
        try:
            access_token_data = {
                "user_id": user_id,
                "scope": scope,
                "token_type": "Bearer",
                "created_at": time.time(),
                "expires_at": time.time() + access_token_expires_in,
                "refresh_token": refresh_token
            }
            
            refresh_token_data = {
                "user_id": user_id,
                "scope": scope,
                "created_at": time.time(),
                "expires_at": time.time() + refresh_token_expires_in,
                "access_token": access_token
            }
            
            if self.use_redis:
                # Store access token
                access_key = self._make_key("access_token", access_token)
                self._redis_client.setex(
                    access_key,
                    access_token_expires_in,
                    self._serialize_data(access_token_data),
                )
                
                # Store refresh token
                refresh_key = self._make_key("refresh_token", refresh_token)
                self._redis_client.setex(
                    refresh_key,
                    refresh_token_expires_in,
                    self._serialize_data(refresh_token_data),
                )
                
                # Store user's tokens for lookup
                user_tokens_key = self._make_key("user_tokens", user_id)
                user_tokens = self._redis_client.get(user_tokens_key)
                tokens_list = json.loads(user_tokens) if user_tokens else []
                tokens_list.append({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "created_at": time.time()
                })
                self._redis_client.setex(
                    user_tokens_key,
                    refresh_token_expires_in,
                    json.dumps(tokens_list),
                )
            else:
                # In-memory storage
                self._in_memory_store[f"access_token:{access_token}"] = access_token_data
                self._in_memory_store[f"refresh_token:{refresh_token}"] = refresh_token_data
                
                # Store user's tokens
                user_tokens_key = f"user_tokens:{user_id}"
                if user_tokens_key not in self._in_memory_store:
                    self._in_memory_store[user_tokens_key] = []
                self._in_memory_store[user_tokens_key].append({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "created_at": time.time()
                })
            
            logger.debug(f"Stored OAuth tokens for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens: {e}")
            return False
    
    async def get_access_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Retrieve access token data"""
        try:
            if self.use_redis:
                key = self._make_key("access_token", access_token)
                data = self._redis_client.get(key)
                if data:
                    token_data = self._deserialize_data(data)
                    # Check expiration
                    if time.time() > token_data.get("expires_at", 0):
                        self._redis_client.delete(key)
                        return None
                    return token_data
            else:
                # In-memory storage
                key = f"access_token:{access_token}"
                if key in self._in_memory_store:
                    token_data = self._in_memory_store[key]
                    # Check expiration
                    if time.time() > token_data.get("expires_at", 0):
                        del self._in_memory_store[key]
                        return None
                    return token_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None
    
    async def get_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Retrieve refresh token data"""
        try:
            if self.use_redis:
                key = self._make_key("refresh_token", refresh_token)
                data = self._redis_client.get(key)
                if data:
                    token_data = self._deserialize_data(data)
                    # Check expiration
                    if time.time() > token_data.get("expires_at", 0):
                        self._redis_client.delete(key)
                        return None
                    return token_data
            else:
                # In-memory storage
                key = f"refresh_token:{refresh_token}"
                if key in self._in_memory_store:
                    token_data = self._in_memory_store[key]
                    # Check expiration
                    if time.time() > token_data.get("expires_at", 0):
                        del self._in_memory_store[key]
                        return None
                    return token_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get refresh token: {e}")
            return None
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke an access token"""
        try:
            if self.use_redis:
                key = self._make_key("access_token", token)
                self._redis_client.delete(key)
            else:
                key = f"access_token:{token}"
                if key in self._in_memory_store:
                    del self._in_memory_store[key]
            
            logger.debug(f"Revoked access token")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    async def store_oauth_session(
        self,
        session_id: str,
        client_id: str,
        redirect_uri: Optional[str],
        scope: str,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        expires_in: int = 1800  # 30 minutes
    ) -> bool:
        """Store OAuth session data"""
        try:
            session_data = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "created_at": time.time(),
                "expires_at": time.time() + expires_in
            }
            
            if self.use_redis:
                key = self._make_key("session", session_id)
                self._redis_client.setex(
                    key,
                    expires_in,
                    self._serialize_data(session_data),
                )
            else:
                # In-memory storage
                self._in_memory_store[f"session:{session_id}"] = session_data
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth session: {e}")
            return False
    
    async def get_oauth_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth session data"""
        try:
            if self.use_redis:
                key = self._make_key("session", session_id)
                data = self._redis_client.get(key)
                if data:
                    session_data = self._deserialize_data(data)
                    # Check expiration
                    if time.time() > session_data.get("expires_at", 0):
                        self._redis_client.delete(key)
                        return None
                    return session_data
            else:
                # In-memory storage
                key = f"session:{session_id}"
                if key in self._in_memory_store:
                    session_data = self._in_memory_store[key]
                    # Check expiration
                    if time.time() > session_data.get("expires_at", 0):
                        del self._in_memory_store[key]
                        return None
                    return session_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get OAuth session: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete OAuth session"""
        try:
            if self.use_redis:
                key = self._make_key("session", session_id)
                self._redis_client.delete(key)
            else:
                key = f"session:{session_id}"
                if key in self._in_memory_store:
                    del self._in_memory_store[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete OAuth session: {e}")
            return False
    
    def cleanup_expired(self):
        """Clean up expired tokens (for in-memory storage)"""
        if self.use_redis:
            # Redis handles expiration automatically
            return
        
        current_time = time.time()
        expired_keys = []
        
        for key, data in self._in_memory_store.items():
            if isinstance(data, dict) and "expires_at" in data:
                if current_time > data["expires_at"]:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self._in_memory_store[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired OAuth tokens")


# Global token store instance
oauth_token_store = OAuthTokenStore()
