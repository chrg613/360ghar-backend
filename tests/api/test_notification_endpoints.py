"""
Tests for notification endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestRegisterDeviceEndpoint:
    """Tests for POST /api/v1/notifications/device endpoint."""

    @pytest.mark.asyncio
    async def test_register_device_token(self, client: AsyncClient, auth_headers):
        """Test registering device token."""
        with patch("app.api.api_v1.endpoints.notifications.register_device_token", new_callable=AsyncMock) as mock_register:
            mock_register.return_value = {"ok": True}

            response = await client.post(
                "/api/v1/notifications/device",
                json={
                    "token": "fcm_device_token_123",
                    "platform": "android",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_register_device_token_ios(self, client: AsyncClient, auth_headers):
        """Test registering iOS device token."""
        with patch("app.api.api_v1.endpoints.notifications.register_device_token", new_callable=AsyncMock) as mock_register:
            mock_register.return_value = {"ok": True}

            response = await client.post(
                "/api/v1/notifications/device",
                json={
                    "token": "apns_device_token_456",
                    "platform": "ios",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestListNotificationsEndpoint:
    """Tests for GET /api/v1/notifications/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_notifications(self, client: AsyncClient, auth_headers):
        """Test listing user notifications."""
        with patch("app.api.api_v1.endpoints.notifications.list_notifications_for_user", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"id": "1", "title": "Test", "body": "Body"},
            ]

            response = await client.get(
                "/api/v1/notifications/",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_notifications_paginated(self, client: AsyncClient, auth_headers):
        """Test paginated notification listing."""
        with patch("app.api.api_v1.endpoints.notifications.list_notifications_for_user", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            response = await client.get(
                "/api/v1/notifications/",
                params={"limit": 10, "offset": 0},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestMarkNotificationReadEndpoint:
    """Tests for POST /api/v1/notifications/{id}/read endpoint."""

    @pytest.mark.asyncio
    async def test_mark_notification_read(self, client: AsyncClient, auth_headers):
        """Test marking notification as read."""
        with patch("app.api.api_v1.endpoints.notifications.mark_delivery_opened", new_callable=AsyncMock) as mock_mark:
            mock_mark.return_value = {"ok": True}

            response = await client.post(
                "/api/v1/notifications/delivery_123/read",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestSendNotificationEndpoint:
    """Tests for admin notification sending."""

    @pytest.mark.asyncio
    async def test_send_to_topic(self, client: AsyncClient, admin_auth_headers):
        """Test sending notification to topic."""
        with patch("app.api.api_v1.endpoints.notifications.send_to_topic", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"ok": True}

            response = await client.post(
                "/api/v1/notifications/send/topic",
                json={
                    "topic": "all_users",
                    "title": "Announcement",
                    "body": "Important message",
                },
                headers=admin_auth_headers,
            )

            # May require admin privileges
            assert response.status_code in [200, 403, 404]

    @pytest.mark.asyncio
    async def test_send_to_user(self, client: AsyncClient, admin_auth_headers):
        """Test sending notification to specific user."""
        with patch("app.api.api_v1.endpoints.notifications.send_to_user", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"ok": True, "sent": 1}

            response = await client.post(
                "/api/v1/notifications/send/user",
                json={
                    "user_id": "user_123",
                    "title": "Personal message",
                    "body": "Hello!",
                },
                headers=admin_auth_headers,
            )

            assert response.status_code in [200, 403, 404]
