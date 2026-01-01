"""
Tests for PM lease service module.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LeaseStatus, UserRole
from app.core.exceptions import BadRequestException, InsufficientPermissionsError


class TestCreateLease:
    """Tests for create_lease function."""

    @pytest.mark.asyncio
    async def test_create_lease_success(
        self,
        db_session: AsyncSession,
        test_user,
        test_property,
    ):
        """Test successful lease creation."""
        from app.services.pm_leases import create_lease

        start = date.today()
        end = start + timedelta(days=365)

        with patch("app.services.pm_leases.assert_can_manage_owner_portfolio", new_callable=AsyncMock):
            with patch("app.services.pm_leases.assert_can_access_property", new_callable=AsyncMock) as mock_prop:
                mock_prop.return_value = test_property

                result = await create_lease(
                    db_session,
                    actor=test_user,
                    owner_id=test_user.id,
                    property_id=test_property.id,
                    tenant_user_id=None,
                    tenant_name="John Tenant",
                    tenant_phone="+919876543210",
                    tenant_email="tenant@example.com",
                    status=LeaseStatus.draft,
                    start_date=start,
                    end_date=end,
                    monthly_rent=50000.0,
                    security_deposit=100000.0,
                )

                assert result is not None
                assert result.property_id == test_property.id
                assert result.monthly_rent == 50000.0

    @pytest.mark.asyncio
    async def test_create_lease_invalid_dates(
        self,
        db_session: AsyncSession,
        test_user,
        test_property,
    ):
        """Test lease creation fails with end_date before start_date."""
        from app.services.pm_leases import create_lease

        start = date.today()
        end = start - timedelta(days=30)  # End before start

        with patch("app.services.pm_leases.assert_can_manage_owner_portfolio", new_callable=AsyncMock):
            with patch("app.services.pm_leases.assert_can_access_property", new_callable=AsyncMock) as mock_prop:
                mock_prop.return_value = test_property

                with pytest.raises(BadRequestException) as exc_info:
                    await create_lease(
                        db_session,
                        actor=test_user,
                        owner_id=test_user.id,
                        property_id=test_property.id,
                        tenant_user_id=None,
                        tenant_name="John Tenant",
                        tenant_phone="+919876543210",
                        tenant_email="tenant@example.com",
                        start_date=start,
                        end_date=end,
                        monthly_rent=50000.0,
                        security_deposit=100000.0,
                    )

                assert "after start_date" in str(exc_info.value.detail)


class TestListLeases:
    """Tests for list_leases function."""

    @pytest.mark.asyncio
    async def test_list_leases_as_owner(
        self,
        db_session: AsyncSession,
        test_user,
        test_leases,
    ):
        """Test listing leases as owner."""
        from app.services.pm_leases import list_leases

        result = await list_leases(
            db_session,
            actor=test_user,
            owner_id=test_user.id,
        )

        assert isinstance(result, list)


class TestGetLease:
    """Tests for get_lease function."""

    @pytest.mark.asyncio
    async def test_get_lease_success(
        self,
        db_session: AsyncSession,
        test_user,
        test_lease,
    ):
        """Test getting lease by ID."""
        from app.services.pm_leases import get_lease

        with patch("app.services.pm_leases.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_lease

            result = await get_lease(db_session, actor=test_user, lease_id=test_lease.id)

            assert result is not None
            assert result.id == test_lease.id


class TestUpdateLease:
    """Tests for update_lease function."""

    @pytest.mark.asyncio
    async def test_update_lease_monthly_rent(
        self,
        db_session: AsyncSession,
        test_user,
        test_lease,
    ):
        """Test updating lease monthly rent."""
        from app.services.pm_leases import update_lease

        with patch("app.services.pm_leases.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_lease

            result = await update_lease(
                db_session,
                actor=test_user,
                lease_id=test_lease.id,
                monthly_rent=55000.0,
            )

            assert result is not None
            assert result.monthly_rent == 55000.0


class TestTerminateLease:
    """Tests for terminate_lease function."""

    @pytest.mark.asyncio
    async def test_terminate_lease_success(
        self,
        db_session: AsyncSession,
        test_user,
        test_active_lease,
    ):
        """Test successful lease termination."""
        from app.services.pm_leases import terminate_lease

        with patch("app.services.pm_leases.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_active_lease

            result = await terminate_lease(
                db_session,
                actor=test_user,
                lease_id=test_active_lease.id,
                termination_reason="Tenant request",
            )

            assert result is not None
            assert result.status == LeaseStatus.terminated


class TestRenewLease:
    """Tests for renew_lease function."""

    @pytest.mark.asyncio
    async def test_renew_lease_success(
        self,
        db_session: AsyncSession,
        test_user,
        test_active_lease,
    ):
        """Test successful lease renewal."""
        from app.services.pm_leases import renew_lease

        new_end_date = test_active_lease.end_date + timedelta(days=365)

        with patch("app.services.pm_leases.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_active_lease
            with patch("app.services.pm_leases.assert_can_access_property", new_callable=AsyncMock):
                with patch("app.services.pm_leases.assert_can_manage_owner_portfolio", new_callable=AsyncMock):
                    result = await renew_lease(
                        db_session,
                        actor=test_user,
                        lease_id=test_active_lease.id,
                        new_end_date=new_end_date,
                        new_monthly_rent=55000.0,
                    )

                    assert result is not None


class TestLeaseStatusTransitions:
    """Tests for lease status transitions."""

    @pytest.mark.asyncio
    async def test_activate_lease(
        self,
        db_session: AsyncSession,
        test_user,
        test_lease,
    ):
        """Test activating a draft lease."""
        from app.services.pm_leases import activate_lease

        with patch("app.services.pm_leases.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_lease
            with patch("app.services.pm_leases.assert_can_access_property", new_callable=AsyncMock) as mock_prop:
                mock_property = MagicMock()
                mock_property.id = test_lease.property_id
                mock_prop.return_value = mock_property

                result = await activate_lease(
                    db_session,
                    actor=test_user,
                    lease_id=test_lease.id,
                )

                assert result is not None
                assert result.status == LeaseStatus.active
