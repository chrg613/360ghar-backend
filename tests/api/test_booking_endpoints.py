"""
Tests for booking endpoints.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestCreateBookingEndpoint:
    """Tests for POST /api/v1/bookings/ endpoint."""

    @pytest.mark.asyncio
    async def test_create_booking_success(self, client: AsyncClient, auth_headers, test_short_stay_property):
        """Test successful booking creation."""
        check_in = datetime.now(timezone.utc) + timedelta(days=7)
        check_out = check_in + timedelta(days=3)

        with patch("app.api.api_v1.endpoints.bookings.create_booking", new_callable=AsyncMock) as mock_create:
            mock_booking = MagicMock()
            mock_booking.id = 1
            mock_booking.booking_reference = "BK12345678"
            mock_booking.property_id = test_short_stay_property.id
            mock_booking.booking_status = "pending"
            mock_booking.payment_status = "pending"
            mock_booking.total_amount = Decimal("7380")
            mock_create.return_value = mock_booking

            response = await client.post(
                "/api/v1/bookings/",
                json={
                    "property_id": test_short_stay_property.id,
                    "check_in_date": check_in.isoformat(),
                    "check_out_date": check_out.isoformat(),
                    "guests": 2,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["booking_reference"] == "BK12345678"

    @pytest.mark.asyncio
    async def test_create_booking_unauthorized(self, client: AsyncClient, test_short_stay_property):
        """Test booking creation without auth."""
        check_in = datetime.now(timezone.utc) + timedelta(days=7)
        check_out = check_in + timedelta(days=3)

        response = await client.post(
            "/api/v1/bookings/",
            json={
                "property_id": test_short_stay_property.id,
                "check_in_date": check_in.isoformat(),
                "check_out_date": check_out.isoformat(),
                "guests": 2,
            },
        )

        assert response.status_code == 401


class TestGetBookingEndpoint:
    """Tests for GET /api/v1/bookings/{booking_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_booking_success(self, client: AsyncClient, auth_headers, test_booking):
        """Test getting booking by ID."""
        with patch("app.api.api_v1.endpoints.bookings.get_booking", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_booking

            response = await client.get(
                f"/api/v1/bookings/{test_booking.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_booking_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent booking."""
        with patch("app.api.api_v1.endpoints.bookings.get_booking", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get(
                "/api/v1/bookings/99999",
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestGetUserBookingsEndpoint:
    """Tests for GET /api/v1/bookings/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_bookings(self, client: AsyncClient, auth_headers):
        """Test getting user's bookings."""
        with patch("app.api.api_v1.endpoints.bookings.get_user_bookings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "bookings": [],
                "total": 0,
                "upcoming": 0,
                "completed": 0,
                "cancelled": 0,
            }

            response = await client.get(
                "/api/v1/bookings/",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "bookings" in data


class TestCancelBookingEndpoint:
    """Tests for POST /api/v1/bookings/{booking_id}/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_booking_success(self, client: AsyncClient, auth_headers, test_booking):
        """Test successful booking cancellation."""
        with patch("app.api.api_v1.endpoints.bookings.cancel_booking", new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True

            response = await client.post(
                f"/api/v1/bookings/{test_booking.id}/cancel",
                json={"reason": "Change of plans"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestCheckAvailabilityEndpoint:
    """Tests for GET /api/v1/bookings/availability endpoint."""

    @pytest.mark.asyncio
    async def test_check_availability(self, client: AsyncClient, test_short_stay_property):
        """Test checking property availability."""
        check_in = datetime.now(timezone.utc) + timedelta(days=7)
        check_out = check_in + timedelta(days=3)

        with patch("app.api.api_v1.endpoints.bookings.check_availability", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "available": True,
                "conflicts": [],
            }

            response = await client.get(
                "/api/v1/bookings/availability",
                params={
                    "property_id": test_short_stay_property.id,
                    "check_in_date": check_in.isoformat(),
                    "check_out_date": check_out.isoformat(),
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "available" in data


class TestGetPricingEndpoint:
    """Tests for GET /api/v1/bookings/pricing endpoint."""

    @pytest.mark.asyncio
    async def test_get_pricing(self, client: AsyncClient, test_short_stay_property):
        """Test getting booking pricing."""
        check_in = datetime.now(timezone.utc) + timedelta(days=7)
        check_out = check_in + timedelta(days=3)

        with patch("app.api.api_v1.endpoints.bookings.calculate_pricing", new_callable=AsyncMock) as mock_price:
            mock_price.return_value = {
                "nights": 3,
                "base_amount": Decimal("6000"),
                "taxes_amount": Decimal("1080"),
                "service_charges": Decimal("300"),
                "discount_amount": Decimal("0"),
                "total_amount": Decimal("7380"),
            }

            response = await client.get(
                "/api/v1/bookings/pricing",
                params={
                    "property_id": test_short_stay_property.id,
                    "check_in_date": check_in.isoformat(),
                    "check_out_date": check_out.isoformat(),
                    "guests": 2,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "total_amount" in data
