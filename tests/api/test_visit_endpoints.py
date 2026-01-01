"""
Tests for visit endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestCreateVisitEndpoint:
    """Tests for POST /api/v1/visits/ endpoint."""

    @pytest.mark.asyncio
    async def test_create_visit_success(self, client: AsyncClient, auth_headers, test_property):
        """Test successful visit creation."""
        scheduled = datetime.now(timezone.utc) + timedelta(days=7)

        with patch("app.api.api_v1.endpoints.visits.create_visit", new_callable=AsyncMock) as mock_create:
            mock_visit = MagicMock()
            mock_visit.id = 1
            mock_visit.property_id = test_property.id
            mock_visit.status = "scheduled"
            mock_visit.scheduled_date = scheduled
            mock_create.return_value = mock_visit

            response = await client.post(
                "/api/v1/visits/",
                json={
                    "property_id": test_property.id,
                    "scheduled_date": scheduled.isoformat(),
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_create_visit_unauthorized(self, client: AsyncClient, test_property):
        """Test visit creation without auth."""
        scheduled = datetime.now(timezone.utc) + timedelta(days=7)

        response = await client.post(
            "/api/v1/visits/",
            json={
                "property_id": test_property.id,
                "scheduled_date": scheduled.isoformat(),
            },
        )

        assert response.status_code == 401


class TestGetVisitEndpoint:
    """Tests for GET /api/v1/visits/{visit_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_visit_success(self, client: AsyncClient, auth_headers, test_visit):
        """Test getting visit by ID."""
        with patch("app.api.api_v1.endpoints.visits.get_visit", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_visit

            response = await client.get(
                f"/api/v1/visits/{test_visit.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_visit_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent visit."""
        with patch("app.api.api_v1.endpoints.visits.get_visit", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get(
                "/api/v1/visits/99999",
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestGetUserVisitsEndpoint:
    """Tests for GET /api/v1/visits/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_visits(self, client: AsyncClient, auth_headers):
        """Test getting user's visits."""
        with patch("app.api.api_v1.endpoints.visits.get_user_visits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "visits": [],
                "total": 0,
                "upcoming": 0,
                "completed": 0,
                "cancelled": 0,
            }

            response = await client.get(
                "/api/v1/visits/",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "visits" in data


class TestGetUpcomingVisitsEndpoint:
    """Tests for GET /api/v1/visits/upcoming endpoint."""

    @pytest.mark.asyncio
    async def test_get_upcoming_visits(self, client: AsyncClient, auth_headers):
        """Test getting upcoming visits."""
        with patch("app.api.api_v1.endpoints.visits.get_user_upcoming_visits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"visits": [], "total": 0}

            response = await client.get(
                "/api/v1/visits/upcoming",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestCancelVisitEndpoint:
    """Tests for POST /api/v1/visits/{visit_id}/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_visit_success(self, client: AsyncClient, auth_headers, test_visit):
        """Test successful visit cancellation."""
        with patch("app.api.api_v1.endpoints.visits.cancel_visit", new_callable=AsyncMock) as mock_cancel:
            mock_visit = MagicMock()
            mock_visit.id = test_visit.id
            mock_visit.status = "cancelled"
            mock_cancel.return_value = mock_visit

            response = await client.post(
                f"/api/v1/visits/{test_visit.id}/cancel",
                json={"reason": "Change of plans"},
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_visit_not_found(self, client: AsyncClient, auth_headers):
        """Test cancelling non-existent visit."""
        with patch("app.api.api_v1.endpoints.visits.cancel_visit", new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = None

            response = await client.post(
                "/api/v1/visits/99999/cancel",
                json={"reason": "Test"},
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestRescheduleVisitEndpoint:
    """Tests for POST /api/v1/visits/{visit_id}/reschedule endpoint."""

    @pytest.mark.asyncio
    async def test_reschedule_visit_success(self, client: AsyncClient, auth_headers, test_visit):
        """Test successful visit reschedule."""
        new_date = datetime.now(timezone.utc) + timedelta(days=14)

        with patch("app.api.api_v1.endpoints.visits.reschedule_visit", new_callable=AsyncMock) as mock_reschedule:
            mock_visit = MagicMock()
            mock_visit.id = test_visit.id
            mock_visit.status = "rescheduled"
            mock_visit.scheduled_date = new_date
            mock_reschedule.return_value = mock_visit

            response = await client.post(
                f"/api/v1/visits/{test_visit.id}/reschedule",
                json={
                    "new_date": new_date.isoformat(),
                    "reason": "Conflict",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestMarkVisitCompletedEndpoint:
    """Tests for POST /api/v1/visits/{visit_id}/complete endpoint."""

    @pytest.mark.asyncio
    async def test_mark_visit_completed(self, client: AsyncClient, auth_headers, test_visit):
        """Test marking visit as completed."""
        with patch("app.api.api_v1.endpoints.visits.mark_visit_completed", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = True

            response = await client.post(
                f"/api/v1/visits/{test_visit.id}/complete",
                json={
                    "notes": "Nice property",
                    "feedback": "Great experience",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
