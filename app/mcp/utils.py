"""
Shared utilities for MCP servers.

Provides common helper functions for database access, user resolution,
and role-based authorization used across both User and Admin MCP servers.
"""
from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from mcp.server.auth.middleware.auth_context import get_access_token as get_auth_access_token

from app.core.database import AsyncSessionLocal
from app.core.auth import verify_supabase_token
from app.core.logging import get_logger
from app.models.enums import UserRole
from app.services.user import get_or_create_user_from_supabase, get_user_by_id

if TYPE_CHECKING:
    from app.models.users import User

logger = get_logger(__name__)


async def get_db():
    """Async generator for database sessions."""
    async with AsyncSessionLocal() as db:
        yield db


def get_user_role(user: "User") -> UserRole:
    """Get the UserRole enum from a user object."""
    try:
        return UserRole(user.role)
    except ValueError:
        return UserRole.user


def is_admin(user: "User") -> bool:
    """Check if user has admin role."""
    return get_user_role(user) == UserRole.admin


def is_agent(user: "User") -> bool:
    """Check if user has agent role."""
    return get_user_role(user) == UserRole.agent


def is_owner_or_above(user: "User") -> bool:
    """Check if user is at least a regular user (can own properties)."""
    role = get_user_role(user)
    return role in (UserRole.user, UserRole.agent, UserRole.admin)


def can_manage_property(user: "User", property_owner_id: int) -> bool:
    """
    Check if user can manage a property (basic check without DB).

    For full authorization with agent scope, use pm_authz.assert_can_access_property.
    """
    role = get_user_role(user)
    if role == UserRole.admin:
        return True
    if property_owner_id == user.id:
        return True
    return False


async def get_user_from_mcp_context(
    db,
    jwt: Optional[str] = None,
    session_jwt: Optional[str] = None,
) -> Optional["User"]:
    """
    Resolve the current authenticated user for MCP tools.

    Priority:
    1. Use the access token from the MCP auth context (OAuth or Supabase JWT)
    2. Fallback to an explicit JWT argument or legacy session JWT

    Args:
        db: AsyncSession database connection
        jwt: Explicit JWT token passed to the tool
        session_jwt: Legacy session JWT stored in memory

    Returns:
        User object or None if not authenticated
    """
    # 1) Authenticated bearer token from MCP HTTP auth (preferred path)
    access_token = get_auth_access_token()
    if access_token is not None:
        claims = getattr(access_token, "claims", {}) or {}
        auth_method = claims.get("auth_method")

        if auth_method == "oauth":
            user_id_raw = claims.get("sub") or claims.get("user_id")
            if not user_id_raw:
                logger.warning("OAuth access token missing user id claim")
                return None
            try:
                user_id = int(user_id_raw)
            except (TypeError, ValueError):
                logger.warning("OAuth access token has invalid user id: %r", user_id_raw)
                return None

            user = await get_user_by_id(db, user_id)
            if not user:
                logger.warning("OAuth access token refers to unknown user id %s", user_id)
            return user

        if auth_method == "supabase_jwt":
            supa_id = claims.get("sub")
            if not supa_id:
                logger.warning("Supabase JWT access token missing sub claim")
                return None
            supa_data = {
                "id": supa_id,
                "email": claims.get("email"),
                "phone": claims.get("phone"),
                "email_verified": claims.get("email_verified", False),
                "user_metadata": claims.get("user_metadata") or {},
            }
            return await get_or_create_user_from_supabase(db, supa_data)

    # 2) Fallback: explicit JWT argument or legacy in-process session JWT
    token = jwt or session_jwt
    if not token:
        return None

    supa = await verify_supabase_token(token)
    if not supa:
        return None
    return await get_or_create_user_from_supabase(db, supa)


def serialize_property_basic(prop: Any) -> dict:
    """Serialize a property object to basic dict for MCP responses."""
    return {
        "id": prop.id,
        "title": prop.title,
        "property_type": getattr(prop, "property_type", None).value if getattr(prop, "property_type", None) else None,
        "purpose": getattr(prop, "purpose", None).value if getattr(prop, "purpose", None) else None,
        "status": getattr(prop, "status", None).value if getattr(prop, "status", None) else None,
        "city": prop.city,
        "locality": prop.locality,
        "full_address": getattr(prop, "full_address", None),
        "price": prop.base_price,
        "monthly_rent": getattr(prop, "monthly_rent", None),
        "daily_rate": getattr(prop, "daily_rate", None),
        "bedrooms": getattr(prop, "bedrooms", None),
        "bathrooms": getattr(prop, "bathrooms", None),
        "area_sqft": getattr(prop, "area_sqft", None),
        "is_available": getattr(prop, "is_available", True),
        "is_managed": getattr(prop, "is_managed", False),
        "management_status": getattr(prop, "management_status", None).value if getattr(prop, "management_status", None) else None,
        "latitude": prop.latitude,
        "longitude": prop.longitude,
        "main_image_url": prop.main_image_url,
        "created_at": prop.created_at.isoformat() if getattr(prop, "created_at", None) else None,
    }


def serialize_property_full(prop: Any) -> dict:
    """Serialize a property object to full dict for MCP responses."""
    basic = serialize_property_basic(prop)
    basic.update({
        "description": prop.description,
        "sub_locality": getattr(prop, "sub_locality", None),
        "landmark": getattr(prop, "landmark", None),
        "pincode": getattr(prop, "pincode", None),
        "state": getattr(prop, "state", None),
        "country": getattr(prop, "country", None),
        "price_per_sqft": getattr(prop, "price_per_sqft", None),
        "security_deposit": getattr(prop, "security_deposit", None),
        "maintenance_charges": getattr(prop, "maintenance_charges", None),
        "balconies": getattr(prop, "balconies", None),
        "parking_spaces": getattr(prop, "parking_spaces", None),
        "floor_number": getattr(prop, "floor_number", None),
        "total_floors": getattr(prop, "total_floors", None),
        "max_occupancy": getattr(prop, "max_occupancy", None),
        "age_of_property": getattr(prop, "age_of_property", None),
        "virtual_tour_url": getattr(prop, "virtual_tour_url", None),
        "video_tour_url": getattr(prop, "video_tour_url", None),
        "features": getattr(prop, "features", None),
        "tags": getattr(prop, "tags", None),
        "available_from": getattr(prop, "available_from", None).isoformat() if getattr(prop, "available_from", None) else None,
        "minimum_stay_days": getattr(prop, "minimum_stay_days", None),
        "owner_name": getattr(prop, "owner_name", None),
        "builder_name": getattr(prop, "builder_name", None),
        "view_count": getattr(prop, "view_count", 0),
        "like_count": getattr(prop, "like_count", 0),
        "payment_due_day": getattr(prop, "payment_due_day", None),
        "grace_period_days": getattr(prop, "grace_period_days", None),
        "late_fee_policy": getattr(prop, "late_fee_policy", None),
        "images": [
            {"url": i.image_url, "caption": getattr(i, "caption", None)}
            for i in (prop.images or [])
        ],
        "amenities": [
            {
                "id": getattr(a, "amenity", a).id if hasattr(a, "amenity") else getattr(a, "id", None),
                "title": getattr(a, "amenity", a).title if hasattr(a, "amenity") else getattr(a, "title", None),
                "icon": getattr(getattr(a, "amenity", a), "icon", None) if hasattr(a, "amenity") else getattr(a, "icon", None),
                "category": getattr(getattr(a, "amenity", a), "category", None) if hasattr(a, "amenity") else getattr(a, "category", None),
            }
            for a in (prop.amenities or [])
        ],
        "updated_at": getattr(prop, "updated_at", None).isoformat() if getattr(prop, "updated_at", None) else None,
    })
    return basic


def serialize_booking(booking: Any) -> dict:
    """Serialize a booking object for MCP responses."""
    return {
        "id": booking.id,
        "booking_reference": getattr(booking, "booking_reference", None),
        "property_id": booking.property_id,
        "user_id": booking.user_id,
        "check_in_date": booking.check_in_date.isoformat() if booking.check_in_date else None,
        "check_out_date": booking.check_out_date.isoformat() if booking.check_out_date else None,
        "guests": getattr(booking, "guests", None),
        "nights": getattr(booking, "nights", None),
        "base_amount": float(getattr(booking, "base_amount", 0) or 0),
        "taxes_amount": float(getattr(booking, "taxes_amount", 0) or 0),
        "service_charges": float(getattr(booking, "service_charges", 0) or 0),
        "discount_amount": float(getattr(booking, "discount_amount", 0) or 0),
        "total_amount": float(getattr(booking, "total_amount", 0) or 0),
        "booking_status": getattr(booking, "booking_status", None),
        "payment_status": getattr(booking, "payment_status", None),
        "payment_method": getattr(booking, "payment_method", None),
        "special_requests": getattr(booking, "special_requests", None),
        "cancellation_reason": getattr(booking, "cancellation_reason", None),
        "cancellation_date": getattr(booking, "cancellation_date", None).isoformat() if getattr(booking, "cancellation_date", None) else None,
        "created_at": booking.created_at.isoformat() if getattr(booking, "created_at", None) else None,
    }


def serialize_lease(lease: Any) -> dict:
    """Serialize a lease object for MCP responses."""
    return {
        "id": lease.id,
        "property_id": lease.property_id,
        "owner_id": getattr(lease, "owner_id", None),
        "tenant_user_id": getattr(lease, "tenant_user_id", None),
        "start_date": lease.start_date.isoformat() if getattr(lease, "start_date", None) else None,
        "end_date": lease.end_date.isoformat() if getattr(lease, "end_date", None) else None,
        "monthly_rent": float(getattr(lease, "monthly_rent", 0) or 0),
        "security_deposit": float(getattr(lease, "security_deposit", 0) or 0),
        "status": getattr(lease, "status", None).value if getattr(lease, "status", None) else None,
        "payment_due_day": getattr(lease, "payment_due_day", None),
        "grace_period_days": getattr(lease, "grace_period_days", None),
        "late_fee_policy": getattr(lease, "late_fee_policy", None),
        "terms": getattr(lease, "terms", None),
        "notes": getattr(lease, "notes", None),
        "created_at": lease.created_at.isoformat() if getattr(lease, "created_at", None) else None,
        "updated_at": getattr(lease, "updated_at", None).isoformat() if getattr(lease, "updated_at", None) else None,
    }


def serialize_maintenance_request(req: Any) -> dict:
    """Serialize a maintenance request for MCP responses."""
    return {
        "id": req.id,
        "property_id": getattr(req, "property_id", None),
        "lease_id": getattr(req, "lease_id", None),
        "reported_by_user_id": getattr(req, "reported_by_user_id", None),
        "title": getattr(req, "title", None),
        "description": getattr(req, "description", None),
        "category": getattr(req, "category", None).value if getattr(req, "category", None) else None,
        "priority": getattr(req, "priority", None).value if getattr(req, "priority", None) else None,
        "status": getattr(req, "status", None).value if getattr(req, "status", None) else None,
        "estimated_cost": float(getattr(req, "estimated_cost", 0) or 0) if getattr(req, "estimated_cost", None) else None,
        "actual_cost": float(getattr(req, "actual_cost", 0) or 0) if getattr(req, "actual_cost", None) else None,
        "scheduled_date": getattr(req, "scheduled_date", None).isoformat() if getattr(req, "scheduled_date", None) else None,
        "completed_date": getattr(req, "completed_date", None).isoformat() if getattr(req, "completed_date", None) else None,
        "vendor_name": getattr(req, "vendor_name", None),
        "vendor_contact": getattr(req, "vendor_contact", None),
        "notes": getattr(req, "notes", None),
        "created_at": req.created_at.isoformat() if getattr(req, "created_at", None) else None,
        "updated_at": getattr(req, "updated_at", None).isoformat() if getattr(req, "updated_at", None) else None,
    }


def serialize_user_basic(user: Any) -> dict:
    """Serialize a user object to basic dict for MCP responses."""
    return {
        "id": user.id,
        "email": getattr(user, "email", None),
        "phone": getattr(user, "phone", None),
        "full_name": getattr(user, "full_name", None),
        "role": getattr(user, "role", "user"),
        "is_verified": getattr(user, "is_verified", False),
        "profile_image_url": getattr(user, "profile_image_url", None),
    }
