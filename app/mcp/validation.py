"""
Input validation schemas for MCP tools.

Provides Pydantic models for validating MCP tool inputs.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class PropertySearchInput(BaseModel):
    """Input validation for property search tool."""
    
    search_query: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: int = Field(5, ge=0, le=50)
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    include_unavailable: bool = False
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v, info):
        """Ensure latitude and longitude are both provided or both None."""
        if v is not None and info.data.get('longitude') is None:
            raise ValueError('longitude must be provided when latitude is specified')
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v, info):
        """Ensure latitude and longitude are both provided or both None."""
        if v is not None and info.data.get('latitude') is None:
            raise ValueError('latitude must be provided when longitude is specified')
        return v


class PropertyGetInput(BaseModel):
    """Input validation for get property tool."""
    
    property_id: int = Field(..., ge=1)


class SwipeInput(BaseModel):
    """Input validation for swipe tools."""
    
    property_id: int = Field(..., ge=1)


class ShortlistListInput(BaseModel):
    """Input validation for shortlist listing."""
    
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class VisitScheduleInput(BaseModel):
    """Input validation for visit scheduling."""
    
    property_id: int = Field(..., ge=1)
    scheduled_date_iso: str = Field(..., description="ISO-8601 formatted datetime")
    special_requirements: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('scheduled_date_iso')
    def validate_datetime(cls, v):
        """Validate ISO-8601 datetime format."""
        try:
            dt = datetime.fromisoformat(v)
            # Ensure date is in the future
            if dt <= datetime.now():
                raise ValueError('scheduled_date must be in the future')
            return v
        except ValueError as e:
            if 'future' in str(e):
                raise e
            raise ValueError('scheduled_date_iso must be valid ISO-8601 format')


class VisitCancelInput(BaseModel):
    """Input validation for visit cancellation."""
    
    visit_id: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1, max_length=500)


class DiscoveryFeedInput(BaseModel):
    """Input validation for discovery feed."""
    
    limit: int = Field(20, ge=1, le=50)


class PropertySearchAdvancedInput(PropertySearchInput):
    """Extended property search with additional filters."""
    
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    property_type: Optional[str] = None
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    amenities: Optional[List[int]] = Field(None, description="List of amenity IDs")
    listing_type: Optional[str] = Field(None, description="rent, sale, or short_stay")
    
    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v, info):
        """Ensure max_price >= min_price if both provided."""
        min_price = info.data.get('min_price')
        if v is not None and min_price is not None and v < min_price:
            raise ValueError('max_price must be greater than or equal to min_price')
        return v
    
    @field_validator('property_type')
    @classmethod
    def validate_property_type(cls, v):
        """Validate property type enum."""
        valid_types = ['apartment', 'villa', 'house', 'office', 'shop', 'land', 'other']
        if v is not None and v.lower() not in valid_types:
            raise ValueError(f'property_type must be one of: {", ".join(valid_types)}')
        return v.lower() if v else None
    
    @field_validator('listing_type')
    @classmethod
    def validate_listing_type(cls, v):
        """Validate listing type enum."""
        valid_types = ['rent', 'sale', 'short_stay']
        if v is not None and v.lower() not in valid_types:
            raise ValueError(f'listing_type must be one of: {", ".join(valid_types)}')
        return v.lower() if v else None


# ============================================================================
# User Profile Validation
# ============================================================================


class UserPreferencesInput(BaseModel):
    """Input validation for user preferences update."""
    
    preferred_locations: Optional[List[str]] = Field(None, description="Preferred city/locality names")
    preferred_property_types: Optional[List[str]] = Field(None, description="Preferred property types")
    preferred_purpose: Optional[str] = Field(None, description="buy, rent, or short_stay")
    price_range_min: Optional[float] = Field(None, ge=0)
    price_range_max: Optional[float] = Field(None, ge=0)
    bedrooms_min: Optional[int] = Field(None, ge=0, le=10)
    bedrooms_max: Optional[int] = Field(None, ge=0, le=10)
    
    @field_validator('price_range_max')
    @classmethod
    def validate_price_range(cls, v, info):
        """Ensure price_range_max >= price_range_min if both provided."""
        min_price = info.data.get('price_range_min')
        if v is not None and min_price is not None and v < min_price:
            raise ValueError('price_range_max must be >= price_range_min')
        return v


# ============================================================================
# Blog Validation
# ============================================================================


class BlogSearchInput(BaseModel):
    """Input validation for blog search."""
    
    query: Optional[str] = Field(None, max_length=200)
    categories: Optional[List[str]] = Field(None, max_length=10)
    tags: Optional[List[str]] = Field(None, max_length=20)
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=50)


class BlogGetInput(BaseModel):
    """Input validation for blog get."""
    
    identifier: str = Field(..., min_length=1, max_length=200, description="Blog post ID or slug")


# ============================================================================
# Auth Validation
# ============================================================================


class RefreshTokenInput(BaseModel):
    """Input validation for token refresh."""
    
    refresh_token: str = Field(..., min_length=20, description="OAuth refresh token")
