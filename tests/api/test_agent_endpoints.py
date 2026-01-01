"""
Tests for agent endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestGetAgentsEndpoint:
    """Tests for GET /api/v1/agents/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_agents_list(self, client: AsyncClient):
        """Test getting agents list."""
        with patch("app.api.api_v1.endpoints.agents.get_available_agents_paginated", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "limit": 20,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

            response = await client.get("/api/v1/agents/")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data


class TestGetAgentByIdEndpoint:
    """Tests for GET /api/v1/agents/{agent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_agent_success(self, client: AsyncClient, test_agent):
        """Test getting agent by ID."""
        with patch("app.api.api_v1.endpoints.agents.get_agent_by_id", new_callable=AsyncMock) as mock_get:
            mock_agent = MagicMock()
            mock_agent.id = test_agent.id
            mock_agent.name = "Test Agent"
            mock_agent.model_dump = MagicMock(return_value={"id": test_agent.id, "name": "Test Agent"})
            mock_get.return_value = mock_agent

            response = await client.get(f"/api/v1/agents/{test_agent.id}")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client: AsyncClient):
        """Test getting non-existent agent."""
        with patch("app.api.api_v1.endpoints.agents.get_agent_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get("/api/v1/agents/99999")

            assert response.status_code == 404


class TestGetMyAgentEndpoint:
    """Tests for GET /api/v1/agents/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_my_agent(self, client: AsyncClient, auth_headers):
        """Test getting current user's assigned agent."""
        with patch("app.api.api_v1.endpoints.agents.get_user_agent", new_callable=AsyncMock) as mock_get:
            mock_agent = MagicMock()
            mock_agent.id = 1
            mock_agent.name = "My Agent"
            mock_agent.model_dump = MagicMock(return_value={"id": 1, "name": "My Agent"})
            mock_get.return_value = mock_agent

            response = await client.get(
                "/api/v1/agents/me",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_my_agent_none_assigned(self, client: AsyncClient, auth_headers):
        """Test when no agent is assigned."""
        with patch("app.api.api_v1.endpoints.agents.get_user_agent", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get(
                "/api/v1/agents/me",
                headers=auth_headers,
            )

            # May return 200 with null or 404 depending on implementation
            assert response.status_code in [200, 404]


class TestAssignAgentEndpoint:
    """Tests for POST /api/v1/agents/assign endpoint."""

    @pytest.mark.asyncio
    async def test_assign_agent_auto(self, client: AsyncClient, auth_headers):
        """Test auto-assigning agent."""
        with patch("app.api.api_v1.endpoints.agents.assign_agent_to_user", new_callable=AsyncMock) as mock_assign:
            mock_assignment = MagicMock()
            mock_assignment.user_id = 1
            mock_assignment.agent = MagicMock()
            mock_assignment.agent.id = 1
            mock_assignment.agent.name = "Agent Smith"
            mock_assign.return_value = mock_assignment

            response = await client.post(
                "/api/v1/agents/assign",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_assign_specific_agent(self, client: AsyncClient, auth_headers, test_agent):
        """Test assigning specific agent."""
        with patch("app.api.api_v1.endpoints.agents.assign_agent_to_user", new_callable=AsyncMock) as mock_assign:
            mock_assignment = MagicMock()
            mock_assignment.user_id = 1
            mock_assignment.agent = MagicMock()
            mock_assignment.agent.id = test_agent.id
            mock_assign.return_value = mock_assignment

            response = await client.post(
                "/api/v1/agents/assign",
                params={"agent_id": test_agent.id},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestGetAgentWithStatsEndpoint:
    """Tests for GET /api/v1/agents/{agent_id}/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_agent_with_stats(self, client: AsyncClient, test_agent):
        """Test getting agent with statistics."""
        with patch("app.api.api_v1.endpoints.agents.get_agent_with_stats", new_callable=AsyncMock) as mock_get:
            mock_agent_stats = MagicMock()
            mock_agent_stats.id = test_agent.id
            mock_agent_stats.stats = MagicMock()
            mock_agent_stats.stats.total_users_assigned = 10
            mock_get.return_value = mock_agent_stats

            response = await client.get(f"/api/v1/agents/{test_agent.id}/stats")

            assert response.status_code == 200


class TestGetAgentsByTypeEndpoint:
    """Tests for GET /api/v1/agents/type/{agent_type} endpoint."""

    @pytest.mark.asyncio
    async def test_get_agents_by_type(self, client: AsyncClient):
        """Test getting agents by type."""
        with patch("app.api.api_v1.endpoints.agents.get_agents_by_type_paginated", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "limit": 20,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

            response = await client.get("/api/v1/agents/type/general")

            assert response.status_code == 200


class TestGetSystemStatsEndpoint:
    """Tests for GET /api/v1/agents/system/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_system_stats(self, client: AsyncClient, admin_auth_headers):
        """Test getting agent system statistics."""
        with patch("app.api.api_v1.endpoints.agents.get_system_stats", new_callable=AsyncMock) as mock_get:
            mock_stats = MagicMock()
            mock_stats.total_agents = 5
            mock_stats.active_agents = 4
            mock_stats.total_users_served = 100
            mock_get.return_value = mock_stats

            response = await client.get(
                "/api/v1/agents/system/stats",
                headers=admin_auth_headers,
            )

            assert response.status_code == 200


class TestUpdateAgentAvailabilityEndpoint:
    """Tests for PATCH /api/v1/agents/{agent_id}/availability endpoint."""

    @pytest.mark.asyncio
    async def test_update_availability(self, client: AsyncClient, admin_auth_headers, test_agent):
        """Test updating agent availability."""
        with patch("app.api.api_v1.endpoints.agents.update_agent_availability", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True

            response = await client.patch(
                f"/api/v1/agents/{test_agent.id}/availability",
                json={"is_available": False},
                headers=admin_auth_headers,
            )

            assert response.status_code == 200
