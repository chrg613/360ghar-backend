# 360Ghar Visit API Documentation

## Overview

The Visit API provides comprehensive functionality for managing property visit scheduling, rescheduling, cancellation, and tracking. This API allows users to schedule visits to properties, view their visit history, and manage their visit bookings.

## Authentication

All visit endpoints require authentication. Include the JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Base URL

All endpoints are prefixed with `/api/v1/visits`

---

## 1. Get Upcoming Visits

**Endpoint:** `GET /visits/upcoming/`  
**Description:** Retrieve all upcoming visits for the authenticated user  
**Authentication:** Required

### Response

**Status Code:** 200 OK

**Response Body:**
```json
{
  "visits": [
    {
      "id": 1,
      "user_id": 123,
      "property_id": 456,
      "agent_id": null,
      "scheduled_date": "2024-12-15T14:30:00Z",
      "actual_date": null,
      "status": "scheduled",
      "special_requirements": "Please show me the garden area",
      "visit_notes": null,
      "visitor_feedback": null,
      "interest_level": null,
      "follow_up_required": false,
      "follow_up_date": null,
      "cancellation_reason": null,
      "rescheduled_from": null,
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": null,
      "property": {
        "id": 456,
        "title": "Modern 3BHK Apartment",
        "description": "Beautiful apartment with modern amenities",
        "price": 8500000,
        "property_type": "apartment",
        "bedrooms": 3,
        "bathrooms": 2,
        "area_sqft": 1200,
        "locality": "Sector 62",
        "city": "Noida",
        "images": [
          {
            "id": 1,
            "image_url": "https://example.com/image1.jpg",
            "is_primary": true
          }
        ]
      }
    }
  ],
  "total": 1
}
```

### Filtering Logic
- Only returns visits with status: `scheduled`, `confirmed`, `rescheduled`
- Only includes visits where `scheduled_date` is in the future
- Visits are ordered by `scheduled_date` (ascending)

---

## 2. Get Past Visits

**Endpoint:** `GET /visits/past/`  
**Description:** Retrieve all past visits for the authenticated user  
**Authentication:** Required

### Response

**Status Code:** 200 OK

**Response Body:**
```json
{
  "visits": [
    {
      "id": 2,
      "user_id": 123,
      "property_id": 789,
      "agent_id": 1,
      "scheduled_date": "2024-11-20T15:00:00Z",
      "actual_date": "2024-11-20T15:30:00Z",
      "status": "completed",
      "special_requirements": null,
      "visit_notes": "Client showed strong interest in the property",
      "visitor_feedback": "Great location and amenities",
      "interest_level": "high",
      "follow_up_required": true,
      "follow_up_date": "2024-11-25T10:00:00Z",
      "cancellation_reason": null,
      "rescheduled_from": null,
      "created_at": "2024-11-15T09:00:00Z",
      "updated_at": "2024-11-20T16:00:00Z",
      "property": {
        "id": 789,
        "title": "Luxury Villa with Garden",
        "description": "Spacious villa with private garden",
        "price": 25000000,
        "property_type": "house",
        "bedrooms": 4,
        "bathrooms": 3,
        "area_sqft": 2500,
        "locality": "Golf Course Road",
        "city": "Gurgaon"
      }
    }
  ],
  "total": 1
}
```

### Filtering Logic
- Returns visits where `scheduled_date` is in the past
- Includes all visit statuses (completed, cancelled, etc.)
- Visits are ordered by `scheduled_date` (descending)

---

## 3. Schedule a Visit

**Endpoint:** `POST /visits/`  
**Description:** Schedule a new property visit  
**Authentication:** Required

### Request Body

**Required Fields:**
```json
{
  "property_id": 456,
  "scheduled_date": "2024-12-20T14:30:00Z"
}
```

**Optional Fields:**
```json
{
  "property_id": 456,
  "scheduled_date": "2024-12-20T14:30:00Z",
  "special_requirements": "I would like to see the basement storage area"
}
```

### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `property_id` | integer | Yes | ID of the property to visit |
| `scheduled_date` | datetime | Yes | Date and time for the visit (ISO 8601 format) |
| `special_requirements` | string | No | Any special requirements or notes for the visit |

### Validation Rules

- `scheduled_date` must be in the future
- `scheduled_date` must include timezone information
- Property with given `property_id` must exist
- User can only schedule visits for properties they have access to

### Success Response

**Status Code:** 201 Created

**Response Body:**
```json
{
  "id": 3,
  "user_id": 123,
  "property_id": 456,
  "agent_id": null,
  "scheduled_date": "2024-12-20T14:30:00Z",
  "actual_date": null,
  "status": "scheduled",
  "special_requirements": "I would like to see the basement storage area",
  "visit_notes": null,
  "visitor_feedback": null,
  "interest_level": null,
  "follow_up_required": false,
  "follow_up_date": null,
  "cancellation_reason": null,
  "rescheduled_from": null,
  "created_at": "2024-12-10T11:00:00Z",
  "updated_at": null,
  "property": {
    "id": 456,
    "title": "Modern 3BHK Apartment",
    "description": "Beautiful apartment with modern amenities",
    "price": 8500000,
    "property_type": "apartment",
    "bedrooms": 3,
    "bathrooms": 2,
    "area_sqft": 1200,
    "locality": "Sector 62",
    "city": "Noida"
  }
}
```

### Error Responses

**Status Code:** 400 Bad Request
```json
{
  "detail": "scheduled_date must be in the future"
}
```

**Status Code:** 404 Not Found
```json
{
  "detail": "Property not found"
}
```

---

## 4. Reschedule a Visit

**Endpoint:** `POST /visits/{visit_id}/reschedule`  
**Description:** Reschedule an existing visit to a new date  
**Authentication:** Required

### Request Body

**Required Fields:**
```json
{
  "new_date": "2024-12-25T16:00:00Z",
  "reason": "Need to reschedule due to prior commitment"
}
```

**Optional Fields:**
```json
{
  "new_date": "2024-12-25T16:00:00Z"
}
```

### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_date` | datetime | Yes | New date and time for the visit (ISO 8601 format) |
| `reason` | string | No | Reason for rescheduling |

### Validation Rules

- Visit must exist and belong to the authenticated user
- Visit status cannot be `cancelled` or `completed`
- `new_date` must be in the future
- `new_date` must include timezone information

### Success Response

**Status Code:** 200 OK

**Response Body:** Updated Visit object
```json
{
  "id": 3,
  "user_id": 123,
  "property_id": 456,
  "agent_id": null,
  "scheduled_date": "2024-12-25T16:00:00Z",
  "actual_date": null,
  "status": "rescheduled",
  "special_requirements": "I would like to see the basement storage area",
  "visit_notes": null,
  "visitor_feedback": null,
  "interest_level": null,
  "follow_up_required": false,
  "follow_up_date": null,
  "cancellation_reason": "Need to reschedule due to prior commitment",
  "rescheduled_from": "2024-12-20T14:30:00Z",
  "created_at": "2024-12-10T11:00:00Z",
  "updated_at": "2024-12-12T12:00:00Z",
  "property": {
    "id": 456,
    "title": "Modern 3BHK Apartment",
    "description": "Beautiful apartment with modern amenities",
    "price": 8500000,
    "property_type": "apartment",
    "bedrooms": 3,
    "bathrooms": 2,
    "area_sqft": 1200,
    "locality": "Sector 62",
    "city": "Noida"
  }
}
```

### Error Responses

**Status Code:** 400 Bad Request
```json
{
  "detail": "Failed to reschedule visit"
}
```

**Status Code:** 403 Forbidden
```json
{
  "detail": "Access denied"
}
```

**Status Code:** 404 Not Found
```json
{
  "detail": "Visit not found"
}
```

---

## 5. Cancel a Visit

**Endpoint:** `POST /visits/{visit_id}/cancel`  
**Description:** Cancel an existing visit  
**Authentication:** Required

### Request Body

**Required Fields:**
```json
{
  "reason": "Unable to make it due to health issues"
}
```

### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | Reason for cancellation |

### Validation Rules

- Visit must exist and belong to the authenticated user
- Visit status cannot be `cancelled` or `completed`

### Success Response

**Status Code:** 200 OK

**Response Body:** Updated Visit object
```json
{
  "id": 3,
  "user_id": 123,
  "property_id": 456,
  "agent_id": null,
  "scheduled_date": "2024-12-25T16:00:00Z",
  "actual_date": null,
  "status": "cancelled",
  "special_requirements": "I would like to see the basement storage area",
  "visit_notes": null,
  "visitor_feedback": null,
  "interest_level": null,
  "follow_up_required": false,
  "follow_up_date": null,
  "cancellation_reason": "Unable to make it due to health issues",
  "rescheduled_from": null,
  "created_at": "2024-12-10T11:00:00Z",
  "updated_at": "2024-12-12T12:05:00Z",
  "property": {
    "id": 456,
    "title": "Modern 3BHK Apartment",
    "description": "Beautiful apartment with modern amenities",
    "price": 8500000,
    "property_type": "apartment",
    "bedrooms": 3,
    "bathrooms": 2,
    "area_sqft": 1200,
    "locality": "Sector 62",
    "city": "Noida"
  }
}
```

### Error Responses

**Status Code:** 400 Bad Request
```json
{
  "detail": "Failed to cancel visit"
}
```

**Status Code:** 403 Forbidden
```json
{
  "detail": "Access denied"
}
```

**Status Code:** 404 Not Found
```json
{
  "detail": "Visit not found"
}
```

---

## 6. Additional Visit Endpoints

### Get All Visits

**Endpoint:** `GET /visits/`  
**Description:** Retrieve all visits for the authenticated user with summary statistics

**Response Body:**
```json
{
  "visits": [...],
  "total": 5,
  "upcoming": 2,
  "completed": 2,
  "cancelled": 1
}
```

### Get Visit Details

**Endpoint:** `GET /visits/{visit_id}`  
**Description:** Retrieve detailed information about a specific visit

### Update Visit Details

**Endpoint:** `PUT /visits/{visit_id}`  
**Description:** Update visit details (admin/agent functionality)

---

## Visit Status Values

The visit status can have the following values:

- `scheduled`: Visit has been scheduled but not yet confirmed
- `confirmed`: Visit has been confirmed by the agent/property owner
- `completed`: Visit has been completed
- `cancelled`: Visit has been cancelled
- `rescheduled`: Visit has been rescheduled to a new date

## Rate Limiting

- All visit endpoints are subject to rate limiting
- Standard rate limits apply (configurable per endpoint)

## Error Handling

All endpoints return standardized error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (access denied)
- `404`: Not Found
- `422`: Unprocessable Entity (validation errors)
- `500`: Internal Server Error

## Best Practices

1. **Always include timezone information** in datetime fields
2. **Validate dates** before sending requests
3. **Handle errors gracefully** with appropriate user feedback
4. **Check visit status** before attempting reschedule/cancel operations
5. **Use descriptive reasons** when rescheduling or cancelling visits

## Example Usage

### JavaScript/Fetch API

```javascript
// Schedule a visit
const scheduleVisit = async (propertyId, scheduledDate) => {
  const response = await fetch('/api/v1/visits/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      property_id: propertyId,
      scheduled_date: scheduledDate,
      special_requirements: 'Please show parking area'
    })
  });

  if (response.ok) {
    const visit = await response.json();
    console.log('Visit scheduled:', visit);
  }
};

// Get upcoming visits
const getUpcomingVisits = async () => {
  const response = await fetch('/api/v1/visits/upcoming/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (response.ok) {
    const data = await response.json();
    console.log('Upcoming visits:', data.visits);
  }
};
```

### Python/Requests

```python
import requests
from datetime import datetime, timezone

# Schedule a visit
def schedule_visit(token, property_id, scheduled_date):
    url = "http://localhost:8000/api/v1/visits/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "property_id": property_id,
        "scheduled_date": scheduled_date.isoformat(),
        "special_requirements": "Please show the rooftop"
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error: {response.json()}")

# Get past visits
def get_past_visits(token):
    url = "http://localhost:8000/api/v1/visits/past/"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.json()}")
```
