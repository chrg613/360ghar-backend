"""
Tests for user repository.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository


class TestUserRepository:
    """Tests for UserRepository class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create a user repository instance."""
        return UserRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_supabase_id(self, repository, mock_session):
        """Test getting user by Supabase ID."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.supabase_user_id = "supabase_123"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_supabase_id("supabase_123")

        assert result == mock_user
        assert result.supabase_user_id == "supabase_123"

    @pytest.mark.asyncio
    async def test_get_by_supabase_id_not_found(self, repository, mock_session):
        """Test getting non-existent user by Supabase ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_supabase_id("non_existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email(self, repository, mock_session):
        """Test getting user by email."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "user@example.com"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_email("user@example.com")

        assert result == mock_user
        assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, repository, mock_session):
        """Test getting non-existent user by email."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_email("notfound@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_phone(self, repository, mock_session):
        """Test getting user by phone."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.phone = "+919876543210"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_phone("+919876543210")

        assert result == mock_user
        assert result.phone == "+919876543210"

    @pytest.mark.asyncio
    async def test_get_by_phone_not_found(self, repository, mock_session):
        """Test getting non-existent user by phone."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_phone("+910000000000")

        assert result is None

    @pytest.mark.asyncio
    async def test_inherits_base_repository_get(self, repository, mock_session):
        """Test that UserRepository inherits get from base."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_session.get.return_value = mock_user

        result = await repository.get(1)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_inherits_base_repository_create(self, repository, mock_session):
        """Test that UserRepository inherits create from base."""
        mock_user = MagicMock()
        mock_user.id = 1

        result = await repository.create(mock_user)

        mock_session.add.assert_called_once_with(mock_user)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_inherits_base_repository_list(self, repository, mock_session):
        """Test that UserRepository inherits list from base."""
        mock_users = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.list()

        assert result == mock_users

    @pytest.mark.asyncio
    async def test_inherits_base_repository_delete(self, repository, mock_session):
        """Test that UserRepository inherits delete from base."""
        mock_user = MagicMock()
        mock_session.get.return_value = mock_user

        result = await repository.delete(1)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_inherits_base_repository_exists(self, repository, mock_session):
        """Test that UserRepository inherits exists from base."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute.return_value = mock_result

        result = await repository.exists(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_inherits_base_repository_count(self, repository, mock_session):
        """Test that UserRepository inherits count from base."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
