"""
Tests for PM maintenance service module.
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MaintenancePriority, MaintenanceRequestStatus


class TestCreateMaintenanceRequest:
    """Tests for create_maintenance_request function."""

    @pytest.mark.asyncio
    async def test_create_maintenance_request_as_tenant(
        self,
        db_session: AsyncSession,
        test_tenant_user,
        test_property,
    ):
        """Test tenant creating maintenance request."""
        from app.services.pm_maintenance import create_maintenance_request

        with patch("app.services.pm_maintenance.assert_can_access_property", new_callable=AsyncMock) as mock_prop:
            mock_prop.return_value = test_property

            result = await create_maintenance_request(
                db_session,
                actor=test_tenant_user,
                property_id=test_property.id,
                title="Leaky faucet",
                description="Kitchen faucet is dripping",
                priority=MaintenancePriority.medium,
                category="plumbing",
            )

            assert result is not None
            assert result.title == "Leaky faucet"
            assert result.status == MaintenanceRequestStatus.open


class TestGetMaintenanceRequest:
    """Tests for get_maintenance_request function."""

    @pytest.mark.asyncio
    async def test_get_maintenance_request_success(
        self,
        db_session: AsyncSession,
        test_user,
        test_maintenance_request,
    ):
        """Test getting maintenance request by ID."""
        from app.services.pm_maintenance import get_maintenance_request

        with patch("app.services.pm_maintenance.assert_can_access_maintenance_request", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_maintenance_request

            result = await get_maintenance_request(
                db_session,
                actor=test_user,
                request_id=test_maintenance_request.id,
            )

            assert result is not None
            assert result.id == test_maintenance_request.id


class TestListMaintenanceRequests:
    """Tests for list_maintenance_requests function."""

    @pytest.mark.asyncio
    async def test_list_requests_for_property(
        self,
        db_session: AsyncSession,
        test_user,
        test_property,
        test_maintenance_requests,
    ):
        """Test listing maintenance requests for property."""
        from app.services.pm_maintenance import list_maintenance_requests

        result = await list_maintenance_requests(
            db_session,
            actor=test_user,
            property_id=test_property.id,
        )

        assert isinstance(result, list)


class TestUpdateMaintenanceRequest:
    """Tests for update_maintenance_request function."""

    @pytest.mark.asyncio
    async def test_update_request_status(
        self,
        db_session: AsyncSession,
        test_user,
        test_maintenance_request,
    ):
        """Test updating maintenance request status."""
        from app.services.pm_maintenance import update_maintenance_request

        with patch("app.services.pm_maintenance.assert_can_access_maintenance_request", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_maintenance_request

            result = await update_maintenance_request(
                db_session,
                actor=test_user,
                request_id=test_maintenance_request.id,
                status=MaintenanceRequestStatus.in_progress,
            )

            assert result is not None
            assert result.status == MaintenanceRequestStatus.in_progress


class TestAssignVendor:
    """Tests for assign_vendor function."""

    @pytest.mark.asyncio
    async def test_assign_vendor_to_request(
        self,
        db_session: AsyncSession,
        test_user,
        test_maintenance_request,
    ):
        """Test assigning vendor to maintenance request."""
        from app.services.pm_maintenance import assign_vendor

        with patch("app.services.pm_maintenance.assert_can_access_maintenance_request", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_maintenance_request

            result = await assign_vendor(
                db_session,
                actor=test_user,
                request_id=test_maintenance_request.id,
                vendor_name="ABC Plumbers",
                vendor_phone="+919876543210",
                estimated_cost=2500.0,
            )

            assert result is not None
            assert result.vendor_name == "ABC Plumbers"


class TestCompleteMaintenanceRequest:
    """Tests for complete_maintenance_request function."""

    @pytest.mark.asyncio
    async def test_complete_request(
        self,
        db_session: AsyncSession,
        test_user,
        test_maintenance_request,
    ):
        """Test completing maintenance request."""
        from app.services.pm_maintenance import complete_maintenance_request

        with patch("app.services.pm_maintenance.assert_can_access_maintenance_request", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_maintenance_request

            result = await complete_maintenance_request(
                db_session,
                actor=test_user,
                request_id=test_maintenance_request.id,
                resolution_notes="Fixed the faucet",
                actual_cost=2000.0,
            )

            assert result is not None
            assert result.status == MaintenanceRequestStatus.completed
            assert result.resolved_at is not None


class TestMaintenancePriority:
    """Tests for maintenance priority handling."""

    def test_priority_enum_values(self):
        """Test priority enum values."""
        assert MaintenancePriority.low.value == "low"
        assert MaintenancePriority.medium.value == "medium"
        assert MaintenancePriority.high.value == "high"
        assert MaintenancePriority.urgent.value == "urgent"

    def test_status_enum_values(self):
        """Test status enum values."""
        assert MaintenanceRequestStatus.open.value == "open"
        assert MaintenanceRequestStatus.in_progress.value == "in_progress"
        assert MaintenanceRequestStatus.completed.value == "completed"
        assert MaintenanceRequestStatus.cancelled.value == "cancelled"
