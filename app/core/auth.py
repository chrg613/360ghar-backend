import anyio
from supabase import create_client, Client
from jose import jwt, JWTError
from app.core.config import settings
from typing import Optional, Dict, Any
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)

# Supabase client for auth only
_supabase_client: Client = None

def get_supabase_auth_client() -> Client:
    """Get Supabase client for authentication only"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client

async def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Supabase JWT token"""
    try:
        supabase = get_supabase_auth_client()
        user_response = await anyio.to_thread.run_sync(
            lambda: supabase.auth.get_user(token)
        )
        if user_response.user:
            # Consider either email or phone confirmation as verification
            user_obj = user_response.user
            is_verified = (user_obj.email_confirmed_at is not None) or (
                getattr(user_obj, "phone_confirmed_at", None) is not None
            )
            return {
                "id": user_obj.id,
                "email": user_obj.email,
                "user_metadata": user_obj.user_metadata,
                "phone": user_obj.phone,
                "email_verified": is_verified,
            }
        return None
    except Exception as e:
        logger.error(f"Error verifying Supabase token: {e}")
        return None


async def admin_find_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Lookup a user via Supabase GoTrue Admin by phone.

    Requires service role key configured in settings.SUPABASE_SECRET_KEY.
    Returns a minimal user dict if found, else None.
    """
    base = settings.SUPABASE_URL.rstrip('/') + '/auth/v1'
    url = f"{base}/admin/users"
    headers = {
        "apikey": settings.SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
    }
    params = {"phone": phone, "per_page": 1}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                # GoTrue returns { users: [...], aud, next_page?, last_page? } in some versions
                users = None
                if isinstance(data, dict) and "users" in data:
                    users = data.get("users") or []
                elif isinstance(data, list):
                    users = data
                else:
                    users = []
                if users:
                    user = users[0]
                    # Ensure match on phone to avoid false positives when server ignores filter
                    if user.get("phone") == phone:
                        return {
                            "id": user.get("id"),
                            "email": user.get("email"),
                            "phone": user.get("phone"),
                            "user_metadata": user.get("user_metadata") or {},
                        }
                    return None
                return None
            # 404 from admin implies not found; treat as None
            if resp.status_code == 404:
                return None
            logger.warning(
                "Admin user lookup by phone failed: %s %s", resp.status_code, resp.text
            )
            return None
    except Exception as e:
        logger.error(f"Admin user lookup error: {e}")
        return None
