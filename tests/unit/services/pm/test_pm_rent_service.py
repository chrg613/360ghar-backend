"""
Tests for PM rent service module.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RentPaymentStatus


class TestGenerateRentCharges:
    """Tests for generate_rent_charges function."""

    @pytest.mark.asyncio
    async def test_generate_monthly_charges(
        self,
        db_session: AsyncSession,
        test_user,
        test_active_lease,
    ):
        """Test generating monthly rent charges."""
        from app.services.pm_rent import generate_rent_charges

        with patch("app.services.pm_rent.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_active_lease

            result = await generate_rent_charges(
                db_session,
                actor=test_user,
                lease_id=test_active_lease.id,
                for_month=date.today().replace(day=1),
            )

            assert result is not None


class TestRecordRentPayment:
    """Tests for record_rent_payment function."""

    @pytest.mark.asyncio
    async def test_record_payment_success(
        self,
        db_session: AsyncSession,
        test_user,
        test_rent_charge,
    ):
        """Test successful rent payment recording."""
        from app.services.pm_rent import record_rent_payment

        with patch("app.services.pm_rent.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_lease = MagicMock()
            mock_lease.id = test_rent_charge.lease_id
            mock_access.return_value = mock_lease

            result = await record_rent_payment(
                db_session,
                actor=test_user,
                charge_id=test_rent_charge.id,
                amount_paid=50000.0,
                payment_method="bank_transfer",
                payment_date=date.today(),
            )

            assert result is not None
            assert result.amount_paid == 50000.0


class TestGetRentHistory:
    """Tests for get_rent_history function."""

    @pytest.mark.asyncio
    async def test_get_rent_history_for_lease(
        self,
        db_session: AsyncSession,
        test_user,
        test_active_lease,
        test_rent_charges,
    ):
        """Test getting rent history for a lease."""
        from app.services.pm_rent import get_rent_history

        with patch("app.services.pm_rent.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_access.return_value = test_active_lease

            result = await get_rent_history(
                db_session,
                actor=test_user,
                lease_id=test_active_lease.id,
            )

            assert isinstance(result, list)


class TestGetOverdueRent:
    """Tests for get_overdue_rent function."""

    @pytest.mark.asyncio
    async def test_get_overdue_rent_charges(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test getting overdue rent charges."""
        from app.services.pm_rent import get_overdue_rent

        result = await get_overdue_rent(
            db_session,
            actor=test_user,
        )

        assert isinstance(result, list)


class TestApplyLateFee:
    """Tests for apply_late_fee function."""

    @pytest.mark.asyncio
    async def test_apply_late_fee(
        self,
        db_session: AsyncSession,
        test_user,
        test_overdue_rent_charge,
    ):
        """Test applying late fee to overdue charge."""
        from app.services.pm_rent import apply_late_fee

        with patch("app.services.pm_rent.assert_can_access_lease", new_callable=AsyncMock) as mock_access:
            mock_lease = MagicMock()
            mock_lease.late_fee_amount = 500.0
            mock_access.return_value = mock_lease

            result = await apply_late_fee(
                db_session,
                actor=test_user,
                charge_id=test_overdue_rent_charge.id,
            )

            assert result is not None
            assert result.late_fee_applied is not None


class TestGetRentSummary:
    """Tests for get_rent_summary function."""

    @pytest.mark.asyncio
    async def test_get_rent_summary_for_property(
        self,
        db_session: AsyncSession,
        test_user,
        test_property,
    ):
        """Test getting rent summary for property."""
        from app.services.pm_rent import get_rent_summary

        result = await get_rent_summary(
            db_session,
            actor=test_user,
            property_id=test_property.id,
        )

        assert "total_collected" in result
        assert "total_outstanding" in result


class TestRentPaymentStatus:
    """Tests for rent payment status transitions."""

    def test_payment_status_values(self):
        """Test payment status enum values."""
        assert RentPaymentStatus.pending.value == "pending"
        assert RentPaymentStatus.paid.value == "paid"
        assert RentPaymentStatus.partial.value == "partial"
        assert RentPaymentStatus.overdue.value == "overdue"
