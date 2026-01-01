"""
Tests for PM (Property Management) endpoints.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestPMDashboardEndpoints:
    """Tests for PM dashboard endpoints."""

    @pytest.mark.asyncio
    async def test_get_dashboard_overview(self, client: AsyncClient, auth_headers):
        """Test getting dashboard overview."""
        with patch("app.api.api_v1.endpoints.pm_dashboard.get_dashboard_overview", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "total_properties": 5,
                "total_tenants": 3,
                "revenue_this_month": 150000,
                "pending_maintenance": 2,
            }

            response = await client.get(
                "/api/v1/pm/dashboard/overview",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_revenue_chart(self, client: AsyncClient, auth_headers):
        """Test getting revenue chart data."""
        with patch("app.api.api_v1.endpoints.pm_dashboard.get_revenue_chart", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "labels": ["Jan", "Feb", "Mar"],
                "data": [100000, 110000, 120000],
            }

            response = await client.get(
                "/api/v1/pm/dashboard/revenue-chart",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPMLeaseEndpoints:
    """Tests for PM lease endpoints."""

    @pytest.mark.asyncio
    async def test_create_lease(self, client: AsyncClient, auth_headers, test_property):
        """Test creating a lease."""
        with patch("app.api.api_v1.endpoints.pm_leases.create_lease", new_callable=AsyncMock) as mock_create:
            mock_lease = MagicMock()
            mock_lease.id = 1
            mock_lease.property_id = test_property.id
            mock_create.return_value = mock_lease

            response = await client.post(
                "/api/v1/pm/leases/",
                json={
                    "property_id": test_property.id,
                    "tenant_name": "John Tenant",
                    "tenant_phone": "+919876543210",
                    "start_date": str(date.today()),
                    "end_date": str(date.today() + timedelta(days=365)),
                    "monthly_rent": 50000,
                    "security_deposit": 100000,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_leases(self, client: AsyncClient, auth_headers):
        """Test listing leases."""
        with patch("app.api.api_v1.endpoints.pm_leases.list_leases", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            response = await client.get(
                "/api/v1/pm/leases/",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_lease(self, client: AsyncClient, auth_headers, test_lease):
        """Test getting lease details."""
        with patch("app.api.api_v1.endpoints.pm_leases.get_lease", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_lease

            response = await client.get(
                f"/api/v1/pm/leases/{test_lease.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPMRentEndpoints:
    """Tests for PM rent endpoints."""

    @pytest.mark.asyncio
    async def test_list_rent_charges(self, client: AsyncClient, auth_headers):
        """Test listing rent charges."""
        with patch("app.api.api_v1.endpoints.pm_rent.list_rent_charges", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            response = await client.get(
                "/api/v1/pm/rent/charges",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_record_payment(self, client: AsyncClient, auth_headers, test_rent_charge):
        """Test recording rent payment."""
        with patch("app.api.api_v1.endpoints.pm_rent.record_rent_payment", new_callable=AsyncMock) as mock_record:
            mock_payment = MagicMock()
            mock_payment.id = 1
            mock_payment.amount_paid = 50000
            mock_record.return_value = mock_payment

            response = await client.post(
                f"/api/v1/pm/rent/charges/{test_rent_charge.id}/payment",
                json={
                    "amount_paid": 50000,
                    "payment_method": "bank_transfer",
                    "payment_date": str(date.today()),
                },
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPMMaintenanceEndpoints:
    """Tests for PM maintenance endpoints."""

    @pytest.mark.asyncio
    async def test_create_maintenance_request(self, client: AsyncClient, auth_headers, test_property):
        """Test creating maintenance request."""
        with patch("app.api.api_v1.endpoints.pm_maintenance.create_maintenance_request", new_callable=AsyncMock) as mock_create:
            mock_request = MagicMock()
            mock_request.id = 1
            mock_request.title = "Leaky faucet"
            mock_create.return_value = mock_request

            response = await client.post(
                "/api/v1/pm/maintenance/",
                json={
                    "property_id": test_property.id,
                    "title": "Leaky faucet",
                    "description": "Kitchen faucet is dripping",
                    "priority": "medium",
                    "category": "plumbing",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_maintenance_requests(self, client: AsyncClient, auth_headers):
        """Test listing maintenance requests."""
        with patch("app.api.api_v1.endpoints.pm_maintenance.list_maintenance_requests", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            response = await client.get(
                "/api/v1/pm/maintenance/",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_maintenance_status(self, client: AsyncClient, auth_headers, test_maintenance_request):
        """Test updating maintenance request status."""
        with patch("app.api.api_v1.endpoints.pm_maintenance.update_maintenance_request", new_callable=AsyncMock) as mock_update:
            mock_request = MagicMock()
            mock_request.id = test_maintenance_request.id
            mock_request.status = "in_progress"
            mock_update.return_value = mock_request

            response = await client.patch(
                f"/api/v1/pm/maintenance/{test_maintenance_request.id}",
                json={"status": "in_progress"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPMTenantEndpoints:
    """Tests for PM tenant endpoints."""

    @pytest.mark.asyncio
    async def test_list_tenants(self, client: AsyncClient, auth_headers):
        """Test listing tenants."""
        with patch("app.api.api_v1.endpoints.pm_tenants.list_tenants", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"items": [], "total": 0}

            response = await client.get(
                "/api/v1/pm/tenants/",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPMExpenseEndpoints:
    """Tests for PM expense endpoints."""

    @pytest.mark.asyncio
    async def test_create_expense(self, client: AsyncClient, auth_headers, test_property):
        """Test creating expense."""
        with patch("app.api.api_v1.endpoints.pm_expenses.create_expense", new_callable=AsyncMock) as mock_create:
            mock_expense = MagicMock()
            mock_expense.id = 1
            mock_expense.amount = 5000
            mock_create.return_value = mock_expense

            response = await client.post(
                "/api/v1/pm/expenses/",
                json={
                    "property_id": test_property.id,
                    "category": "maintenance",
                    "amount": 5000,
                    "description": "Plumbing repair",
                    "expense_date": str(date.today()),
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_expenses(self, client: AsyncClient, auth_headers):
        """Test listing expenses."""
        with patch("app.api.api_v1.endpoints.pm_expenses.list_expenses", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"items": [], "total": 0}

            response = await client.get(
                "/api/v1/pm/expenses/",
                headers=auth_headers,
            )

            assert response.status_code == 200
