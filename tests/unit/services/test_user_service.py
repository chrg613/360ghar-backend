"""
Tests for user service module.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BaseAPIException
from app.models.users import User
from app.models.enums import UserRole


class TestGetUserByPhone:
    """Tests for get_user_by_phone function."""

    @pytest.mark.asyncio
    async def test_get_user_by_phone_found(self, db_session: AsyncSession, test_user):
        """Test finding user by phone number."""
        from app.services.user import get_user_by_phone

        result = await get_user_by_phone(db_session, test_user.phone)

        assert result is not None
        assert result.id == test_user.id
        assert result.phone == test_user.phone

    @pytest.mark.asyncio
    async def test_get_user_by_phone_not_found(self, db_session: AsyncSession):
        """Test when user not found by phone."""
        from app.services.user import get_user_by_phone

        result = await get_user_by_phone(db_session, "+919999999999")

        assert result is None


class TestGetUserByEmail:
    """Tests for get_user_by_email function."""

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, db_session: AsyncSession, test_user):
        """Test finding user by email."""
        from app.services.user import get_user_by_email

        result = await get_user_by_email(db_session, test_user.email)

        assert result is not None
        assert result.id == test_user.id
        assert result.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_session: AsyncSession):
        """Test when user not found by email."""
        from app.services.user import get_user_by_email

        result = await get_user_by_email(db_session, "nonexistent@example.com")

        assert result is None


class TestGetUserBySupabaseId:
    """Tests for get_user_by_supabase_id function."""

    @pytest.mark.asyncio
    async def test_get_user_by_supabase_id_found(self, db_session: AsyncSession, test_user):
        """Test finding user by Supabase ID."""
        from app.services.user import get_user_by_supabase_id

        result = await get_user_by_supabase_id(db_session, test_user.supabase_user_id)

        assert result is not None
        assert result.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_supabase_id_not_found(self, db_session: AsyncSession):
        """Test when user not found by Supabase ID."""
        from app.services.user import get_user_by_supabase_id

        result = await get_user_by_supabase_id(db_session, str(uuid.uuid4()))

        assert result is None


class TestGetOrCreateUserFromSupabase:
    """Tests for get_or_create_user_from_supabase function."""

    @pytest.mark.asyncio
    async def test_get_existing_user_by_supabase_id(self, db_session: AsyncSession, test_user):
        """Test getting existing user by Supabase ID."""
        from app.services.user import get_or_create_user_from_supabase

        supabase_data = {
            "id": test_user.supabase_user_id,
            "phone": test_user.phone,
            "email": test_user.email,
            "email_verified": True,
            "user_metadata": {"full_name": test_user.full_name},
        }

        result = await get_or_create_user_from_supabase(db_session, supabase_data)

        assert result is not None
        assert result.id == test_user.id

    @pytest.mark.asyncio
    async def test_create_new_user(self, db_session: AsyncSession):
        """Test creating new user from Supabase data."""
        from app.services.user import get_or_create_user_from_supabase

        new_supabase_id = str(uuid.uuid4())
        supabase_data = {
            "id": new_supabase_id,
            "phone": "+919111222333",
            "email": "newuser@example.com",
            "email_verified": True,
            "user_metadata": {"full_name": "New User"},
        }

        result = await get_or_create_user_from_supabase(db_session, supabase_data)

        assert result is not None
        assert result.supabase_user_id == new_supabase_id
        assert result.phone == "+919111222333"
        assert result.email == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_link_existing_user_by_phone(self, db_session: AsyncSession, test_user):
        """Test linking existing user by phone to new Supabase ID."""
        from app.services.user import get_or_create_user_from_supabase

        # Create user without Supabase ID
        user_without_supabase = User(
            supabase_user_id=str(uuid.uuid4()),
            phone="+919444555666",
            email="existing@example.com",
            full_name="Existing User",
            role=UserRole.user.value,
            is_active=True,
        )
        db_session.add(user_without_supabase)
        await db_session.flush()

        new_supabase_id = str(uuid.uuid4())
        supabase_data = {
            "id": new_supabase_id,
            "phone": "+919444555666",
            "email": "existing@example.com",
            "email_verified": True,
            "user_metadata": {},
        }

        result = await get_or_create_user_from_supabase(db_session, supabase_data)

        assert result is not None
        assert result.phone == "+919444555666"


class TestUserRoles:
    """Tests for user role handling."""

    @pytest.mark.asyncio
    async def test_user_has_user_role(self, test_user):
        """Test user has correct role."""
        assert test_user.role == UserRole.user.value

    @pytest.mark.asyncio
    async def test_admin_user_has_admin_role(self, test_admin_user):
        """Test admin user has correct role."""
        assert test_admin_user.role == UserRole.admin.value

    @pytest.mark.asyncio
    async def test_agent_user_has_agent_role(self, test_agent_user):
        """Test agent user has correct role."""
        assert test_agent_user.role == UserRole.agent.value


class TestUpdateUser:
    """Tests for update_user function."""

    @pytest.mark.asyncio
    async def test_update_user_unexpected_error_is_wrapped(self):
        """Unexpected update errors should stay in the standard API envelope."""
        from app.schemas.user import UserUpdate
        from app.services.user import update_user

        db = AsyncMock(spec=AsyncSession)
        db.flush.side_effect = RuntimeError("boom")

        existing_user = User(
            id=1,
            supabase_user_id=str(uuid.uuid4()),
            phone="+919876543210",
            email="test@example.com",
            full_name="Test User",
            role=UserRole.user.value,
            is_active=True,
        )

        with patch("app.services.user.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = existing_user

            with pytest.raises(BaseAPIException) as exc_info:
                await update_user(
                    db,
                    1,
                    UserUpdate(full_name="Updated Name"),
                    actor=existing_user,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error occurred while updating user"
