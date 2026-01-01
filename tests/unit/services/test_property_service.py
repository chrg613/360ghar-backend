"""
Tests for property service module.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.properties import Property
from app.models.enums import PropertyType, PropertyPurpose, PropertyStatus


class TestCreateProperty:
    """Tests for create_property function."""

    @pytest.mark.asyncio
    async def test_create_property_success(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test successful property creation."""
        from app.services.property import create_property
        from app.schemas.property import PropertyCreate

        property_data = PropertyCreate(
            title="New Test Property",
            description="A beautiful test property",
            property_type=PropertyType.apartment,
            purpose=PropertyPurpose.rent,
            monthly_rent=Decimal("50000"),
            city="Mumbai",
            locality="Andheri",
            full_address="123 Test Street, Andheri, Mumbai",
            pincode="400069",
            state="Maharashtra",
            country="India",
            latitude=19.1136,
            longitude=72.8697,
            bedrooms=2,
            bathrooms=2,
            area_sqft=Decimal("1000"),
        )

        result = await create_property(db_session, property_data, test_user.id, test_user)

        assert result is not None
        assert result.title == "New Test Property"
        assert result.owner_id == test_user.id
        assert result.property_type == PropertyType.apartment


class TestGetProperty:
    """Tests for get_property function."""

    @pytest.mark.asyncio
    async def test_get_property_success(
        self,
        db_session: AsyncSession,
        test_property,
    ):
        """Test getting property by ID."""
        from app.services.property import get_property

        result = await get_property(db_session, test_property.id)

        assert result is not None
        assert result.id == test_property.id
        assert result.title == test_property.title

    @pytest.mark.asyncio
    async def test_get_property_not_found(self, db_session: AsyncSession):
        """Test getting non-existent property."""
        from app.services.property import get_property

        result = await get_property(db_session, 99999)

        assert result is None


class TestUpdateProperty:
    """Tests for update_property function."""

    @pytest.mark.asyncio
    async def test_update_property_success(
        self,
        db_session: AsyncSession,
        test_property,
        test_user,
    ):
        """Test successful property update."""
        from app.services.property import update_property
        from app.schemas.property import PropertyUpdate

        update_data = PropertyUpdate(title="Updated Title")

        result = await update_property(
            db_session, test_property.id, update_data, test_user
        )

        assert result is not None
        assert result.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_property_not_found(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test updating non-existent property."""
        from app.services.property import update_property
        from app.schemas.property import PropertyUpdate
        from fastapi import HTTPException

        update_data = PropertyUpdate(title="Updated Title")

        with pytest.raises(HTTPException) as exc_info:
            await update_property(db_session, 99999, update_data, test_user)

        assert exc_info.value.status_code == 404


class TestDeleteProperty:
    """Tests for delete_property function."""

    @pytest.mark.asyncio
    async def test_delete_property_success(
        self,
        db_session: AsyncSession,
        test_property,
        test_user,
    ):
        """Test successful property deletion."""
        from app.services.property import delete_property, get_property

        property_id = test_property.id

        result = await delete_property(db_session, property_id, test_user)

        assert result is True

        # Verify deleted
        deleted = await get_property(db_session, property_id)
        assert deleted is None


class TestListUserProperties:
    """Tests for list_user_properties function."""

    @pytest.mark.asyncio
    async def test_list_user_properties(
        self,
        db_session: AsyncSession,
        test_user,
        test_properties,
    ):
        """Test listing properties for a user."""
        from app.services.property import list_user_properties

        result = await list_user_properties(db_session, test_user.id)

        assert len(result) == len(test_properties)


class TestPropertyFiltering:
    """Tests for property filtering."""

    @pytest.mark.asyncio
    async def test_filter_by_city(
        self,
        db_session: AsyncSession,
        test_properties,
    ):
        """Test filtering properties by city."""
        from app.services.property import get_unified_properties_optimized
        from app.schemas.property import UnifiedPropertyFilter

        filters = UnifiedPropertyFilter(city="Mumbai")

        result = await get_unified_properties_optimized(
            db_session, filters, page=1, limit=10
        )

        assert "items" in result
        for prop in result["items"]:
            assert prop.city == "Mumbai"

    @pytest.mark.asyncio
    async def test_filter_by_purpose(
        self,
        db_session: AsyncSession,
        test_properties,
    ):
        """Test filtering properties by purpose."""
        from app.services.property import get_unified_properties_optimized
        from app.schemas.property import UnifiedPropertyFilter

        filters = UnifiedPropertyFilter(purpose=PropertyPurpose.rent)

        result = await get_unified_properties_optimized(
            db_session, filters, page=1, limit=10
        )

        assert "items" in result
        for prop in result["items"]:
            assert prop.purpose == PropertyPurpose.rent

    @pytest.mark.asyncio
    async def test_filter_by_property_type(
        self,
        db_session: AsyncSession,
        test_properties,
    ):
        """Test filtering properties by type."""
        from app.services.property import get_unified_properties_optimized
        from app.schemas.property import UnifiedPropertyFilter

        filters = UnifiedPropertyFilter(property_type=[PropertyType.apartment])

        result = await get_unified_properties_optimized(
            db_session, filters, page=1, limit=10
        )

        assert "items" in result
        for prop in result["items"]:
            assert prop.property_type == PropertyType.apartment


class TestPropertyViewCount:
    """Tests for property view count functionality."""

    @pytest.mark.asyncio
    async def test_increment_view_count(
        self,
        db_session: AsyncSession,
        test_property,
    ):
        """Test incrementing property view count."""
        from app.services.property import increment_property_view_count

        initial_views = test_property.view_count or 0

        await increment_property_view_count(db_session, test_property.id)

        await db_session.refresh(test_property)
        assert test_property.view_count == initial_views + 1


class TestPropertyRecommendations:
    """Tests for property recommendations."""

    @pytest.mark.asyncio
    async def test_get_recommendations(
        self,
        db_session: AsyncSession,
        test_user,
        test_properties,
    ):
        """Test getting property recommendations."""
        from app.services.property import get_property_recommendations

        result = await get_property_recommendations(
            db_session,
            user_id=test_user.id,
            limit=5,
        )

        assert isinstance(result, list)
