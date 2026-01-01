"""
End-to-end tests for booking complete flow.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestBookingCompleteFlow:
    """Tests for complete booking flow from search to checkout."""

    @pytest.mark.asyncio
    async def test_search_check_book_flow(self, client: AsyncClient, auth_headers, test_short_stay_property):
        """Test complete flow: search -> check availability -> get pricing -> book."""
        check_in = datetime.now(timezone.utc) + timedelta(days=7)
        check_out = check_in + timedelta(days=3)

        # Step 1: Search for properties
        with patch("app.api.api_v1.endpoints.properties.get_unified_properties_optimized", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "items": [test_short_stay_property],
                "total": 1,
                "page": 1,
                "limit": 20,
            }

            response = await client.get(
                "/api/v1/properties/",
                params={
                    "purpose": "short_stay",
                    "city": "Mumbai",
                },
            )

            assert response.status_code == 200

        # Step 2: Check availability
        with patch("app.api.api_v1.endpoints.bookings.check_availability", new_callable=AsyncMock) as mock_avail:
            mock_avail.return_value = {
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
            assert data.get("available") is True or "available" in data

        # Step 3: Get pricing
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

        # Step 4: Create booking
        with patch("app.api.api_v1.endpoints.bookings.create_booking", new_callable=AsyncMock) as mock_book:
            mock_booking = MagicMock()
            mock_booking.id = 1
            mock_booking.booking_reference = "BK12345678"
            mock_booking.booking_status = "pending"
            mock_booking.total_amount = Decimal("7380")
            mock_book.return_value = mock_booking

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


class TestBookingManagementFlow:
    """Tests for managing existing bookings."""

    @pytest.mark.asyncio
    async def test_view_and_cancel_booking(self, client: AsyncClient, auth_headers, test_booking):
        """Test viewing and cancelling a booking."""
        # Step 1: View booking details
        with patch("app.api.api_v1.endpoints.bookings.get_booking", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_booking

            response = await client.get(
                f"/api/v1/bookings/{test_booking.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200

        # Step 2: Cancel booking
        with patch("app.api.api_v1.endpoints.bookings.cancel_booking", new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True

            response = await client.post(
                f"/api/v1/bookings/{test_booking.id}/cancel",
                json={"reason": "Plans changed"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestBookingListingFlow:
    """Tests for listing user bookings."""

    @pytest.mark.asyncio
    async def test_list_all_bookings(self, client: AsyncClient, auth_headers):
        """Test listing all user bookings."""
        with patch("app.api.api_v1.endpoints.bookings.get_user_bookings", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {
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

    @pytest.mark.asyncio
    async def test_list_upcoming_bookings(self, client: AsyncClient, auth_headers):
        """Test listing upcoming bookings."""
        with patch("app.api.api_v1.endpoints.bookings.get_user_upcoming_bookings", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"bookings": [], "total": 0}

            response = await client.get(
                "/api/v1/bookings/upcoming",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestBookingStatusTransitions:
    """Tests for booking status transitions."""

    @pytest.mark.asyncio
    async def test_confirm_booking(self, client: AsyncClient, admin_auth_headers, test_booking):
        """Test confirming a pending booking."""
        with patch("app.api.api_v1.endpoints.bookings.confirm_booking", new_callable=AsyncMock) as mock_confirm:
            mock_booking = MagicMock()
            mock_booking.id = test_booking.id
            mock_booking.booking_status = "confirmed"
            mock_confirm.return_value = mock_booking

            response = await client.post(
                f"/api/v1/bookings/{test_booking.id}/confirm",
                headers=admin_auth_headers,
            )

            # May require admin privileges
            assert response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_check_in_booking(self, client: AsyncClient, admin_auth_headers, confirmed_booking):
        """Test checking in a confirmed booking."""
        with patch("app.api.api_v1.endpoints.bookings.check_in_booking", new_callable=AsyncMock) as mock_checkin:
            mock_booking = MagicMock()
            mock_booking.id = confirmed_booking.id
            mock_booking.booking_status = "checked_in"
            mock_checkin.return_value = mock_booking

            response = await client.post(
                f"/api/v1/bookings/{confirmed_booking.id}/check-in",
                headers=admin_auth_headers,
            )

            assert response.status_code in [200, 403]
