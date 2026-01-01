"""
Sample data fixtures for testing.

Provides pre-built test data scenarios for common testing needs.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.models.properties import Property, Amenity
from app.models.bookings import Booking
from app.models.enums import (
    PropertyType,
    PropertyPurpose,
    PropertyStatus,
    BookingStatus,
    PaymentStatus,
)
from tests.fixtures.factories import (
    UserFactory,
    PropertyFactory,
    BookingFactory,
    AmenityFactory,
)


# =============================================================================
# Property Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_property(db_session, test_user) -> Property:
    """
    Create a single test property owned by test_user.

    Returns:
        Property for rent in Mumbai
    """
    return await PropertyFactory.create(
        db_session,
        owner=test_user,
        title="Test Apartment",
        description="A beautiful 2BHK apartment for rent",
        property_type=PropertyType.apartment,
        purpose=PropertyPurpose.rent,
        monthly_rent=Decimal("50000"),
        city="Mumbai",
        locality="Andheri",
        bedrooms=2,
        bathrooms=2,
    )


@pytest_asyncio.fixture
async def test_short_stay_property(db_session, test_user) -> Property:
    """
    Create a short-stay property for booking tests.

    Returns:
        Property for short_stay with daily rate
    """
    return await PropertyFactory.create(
        db_session,
        owner=test_user,
        title="Vacation Stay Property",
        description="Perfect for short vacation stays",
        property_type=PropertyType.apartment,
        purpose=PropertyPurpose.short_stay,
        daily_rate=Decimal("2000"),
        city="Mumbai",
        locality="Bandra",
        bedrooms=1,
        bathrooms=1,
    )


@pytest_asyncio.fixture
async def test_properties(db_session, test_user) -> List[Property]:
    """
    Create multiple properties for list/search tests.

    Returns:
        List of 5 properties with varied attributes
    """
    properties = []

    # Property 1: Apartment for rent
    properties.append(
        await PropertyFactory.create(
            db_session,
            owner=test_user,
            title="Modern Apartment in Andheri",
            property_type=PropertyType.apartment,
            purpose=PropertyPurpose.rent,
            monthly_rent=Decimal("45000"),
            city="Mumbai",
            locality="Andheri",
            latitude=19.1136,
            longitude=72.8697,
            bedrooms=2,
            bathrooms=2,
        )
    )

    # Property 2: House for buy
    properties.append(
        await PropertyFactory.create(
            db_session,
            owner=test_user,
            title="Spacious House in Bandra",
            property_type=PropertyType.house,
            purpose=PropertyPurpose.buy,
            base_price=Decimal("25000000"),
            city="Mumbai",
            locality="Bandra",
            latitude=19.0544,
            longitude=72.8406,
            bedrooms=4,
            bathrooms=3,
        )
    )

    # Property 3: Room for rent
    properties.append(
        await PropertyFactory.create(
            db_session,
            owner=test_user,
            title="Cozy Room in Powai",
            property_type=PropertyType.room,
            purpose=PropertyPurpose.rent,
            monthly_rent=Decimal("15000"),
            city="Mumbai",
            locality="Powai",
            latitude=19.1176,
            longitude=72.9060,
            bedrooms=1,
            bathrooms=1,
        )
    )

    # Property 4: Short stay apartment
    properties.append(
        await PropertyFactory.create(
            db_session,
            owner=test_user,
            title="Holiday Apartment in Colaba",
            property_type=PropertyType.apartment,
            purpose=PropertyPurpose.short_stay,
            daily_rate=Decimal("3500"),
            city="Mumbai",
            locality="Colaba",
            latitude=18.9067,
            longitude=72.8147,
            bedrooms=2,
            bathrooms=1,
        )
    )

    # Property 5: Builder floor for buy
    properties.append(
        await PropertyFactory.create(
            db_session,
            owner=test_user,
            title="Builder Floor in Juhu",
            property_type=PropertyType.builder_floor,
            purpose=PropertyPurpose.buy,
            base_price=Decimal("35000000"),
            city="Mumbai",
            locality="Juhu",
            latitude=19.0989,
            longitude=72.8265,
            bedrooms=3,
            bathrooms=2,
        )
    )

    return properties


# =============================================================================
# Booking Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_booking(
    db_session,
    test_user_2,
    test_short_stay_property,
) -> Booking:
    """
    Create a pending booking for test_user_2.

    Uses test_short_stay_property (owned by test_user).
    """
    return await BookingFactory.create(
        db_session,
        user=test_user_2,
        property_obj=test_short_stay_property,
        check_in_date=datetime.now() + timedelta(days=7),
        check_out_date=datetime.now() + timedelta(days=10),
        guests=2,
        booking_status=BookingStatus.pending,
    )


@pytest_asyncio.fixture
async def confirmed_booking(
    db_session,
    test_user_2,
    test_short_stay_property,
) -> Booking:
    """Create a confirmed and paid booking."""
    return await BookingFactory.create(
        db_session,
        user=test_user_2,
        property_obj=test_short_stay_property,
        check_in_date=datetime.now() + timedelta(days=14),
        check_out_date=datetime.now() + timedelta(days=17),
        guests=2,
        booking_status=BookingStatus.confirmed,
        payment_status=PaymentStatus.paid,
    )


@pytest_asyncio.fixture
async def test_bookings(
    db_session,
    test_user,
    test_short_stay_property,
) -> List[Booking]:
    """
    Create multiple bookings with different statuses.

    Returns:
        List of bookings: pending, confirmed, completed, cancelled
    """
    bookings = []

    # Pending booking
    bookings.append(
        await BookingFactory.create(
            db_session,
            user=test_user,
            property_obj=test_short_stay_property,
            check_in_date=datetime.now() + timedelta(days=7),
            check_out_date=datetime.now() + timedelta(days=10),
            booking_status=BookingStatus.pending,
        )
    )

    # Confirmed upcoming booking
    bookings.append(
        await BookingFactory.create(
            db_session,
            user=test_user,
            property_obj=test_short_stay_property,
            check_in_date=datetime.now() + timedelta(days=14),
            check_out_date=datetime.now() + timedelta(days=17),
            booking_status=BookingStatus.confirmed,
            payment_status=PaymentStatus.paid,
        )
    )

    # Completed past booking
    bookings.append(
        await BookingFactory.create(
            db_session,
            user=test_user,
            property_obj=test_short_stay_property,
            check_in_date=datetime.now() - timedelta(days=30),
            check_out_date=datetime.now() - timedelta(days=27),
            booking_status=BookingStatus.completed,
            payment_status=PaymentStatus.paid,
        )
    )

    # Cancelled booking
    bookings.append(
        await BookingFactory.create(
            db_session,
            user=test_user,
            property_obj=test_short_stay_property,
            check_in_date=datetime.now() + timedelta(days=21),
            check_out_date=datetime.now() + timedelta(days=24),
            booking_status=BookingStatus.cancelled,
        )
    )

    return bookings


# =============================================================================
# Amenity Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_amenities(db_session) -> List[Amenity]:
    """
    Create a set of common amenities.

    Returns:
        List of 10 amenities
    """
    amenities = []
    amenity_data = [
        ("Swimming Pool", "pool", "recreation"),
        ("Gym", "fitness", "recreation"),
        ("Parking", "car", "convenience"),
        ("24x7 Security", "shield", "safety"),
        ("Garden", "leaf", "recreation"),
        ("Club House", "home", "recreation"),
        ("Power Backup", "bolt", "convenience"),
        ("Lift", "elevator", "convenience"),
        ("Wi-Fi", "wifi", "convenience"),
        ("Air Conditioning", "snowflake", "convenience"),
    ]

    for title, icon, category in amenity_data:
        amenity = await AmenityFactory.create(
            db_session,
            title=title,
            icon=icon,
            category=category,
        )
        amenities.append(amenity)

    return amenities


# =============================================================================
# Complete Scenario Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def property_with_bookings(
    db_session,
    test_user,
    test_user_2,
) -> dict:
    """
    Create a complete scenario with property and multiple bookings.

    Returns:
        Dict with 'property', 'owner', 'guest', and 'bookings'
    """
    # Create property
    property_obj = await PropertyFactory.create(
        db_session,
        owner=test_user,
        title="Beachside Villa",
        purpose=PropertyPurpose.short_stay,
        daily_rate=Decimal("5000"),
    )

    # Create bookings by different user
    bookings = []

    # Upcoming booking
    bookings.append(
        await BookingFactory.create(
            db_session,
            user=test_user_2,
            property_obj=property_obj,
            check_in_date=datetime.now() + timedelta(days=5),
            check_out_date=datetime.now() + timedelta(days=8),
            booking_status=BookingStatus.confirmed,
        )
    )

    # Past booking
    bookings.append(
        await BookingFactory.create(
            db_session,
            user=test_user_2,
            property_obj=property_obj,
            check_in_date=datetime.now() - timedelta(days=10),
            check_out_date=datetime.now() - timedelta(days=7),
            booking_status=BookingStatus.completed,
        )
    )

    return {
        "property": property_obj,
        "owner": test_user,
        "guest": test_user_2,
        "bookings": bookings,
    }
