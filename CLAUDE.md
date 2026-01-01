# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Platform Overview

360 Ghar is a unified real estate platform with three integrated modules:

- **360 Ghar Core**: Real estate marketplace for buying and renting properties with swipe-based discovery, property visits, and agent coordination (`/api/v1/properties`, `/swipes`, `/visits`, `/agents`)
- **360 Stays**: Short-stay booking platform for hotels, vacation rentals, and temporary accommodations (`/api/v1/bookings`)
- **Property Management**: Comprehensive property management system for landlords and property managers (`/api/v1/pm/*`)

## Build and Development Commands

### Running the API
```bash
python run.py                                      # Simple start
fastapi dev app/main.py --host 0.0.0.0 --port 8000 # Hot reload (recommended)
```

### Testing
```bash
pytest tests/ -v                              # All tests
pytest tests/test_user_service.py -v         # Specific file
pytest tests/ -k "user" -v                   # By keyword
pytest tests/test_file.py::test_func -v      # Single test
pytest tests/ --cov=app --cov-report=html    # With coverage
```

### Data Population
```bash
PYTHONPATH=$(pwd) python populate_data/load_comprehensive_data.py          # Full dataset (~300 properties)
PYTHONPATH=$(pwd) python populate_data/load_comprehensive_data.py --quick  # Quick load (~51 properties)
PYTHONPATH=$(pwd) python populate_data/load_comprehensive_data.py --clear  # Clear first, then load
```

### Database
```bash
supabase db reset   # Reset local database
supabase db push    # Apply migrations
supabase db diff    # Check pending changes
```

## Architecture Overview

### Layered Structure
```
app/
├── api/api_v1/endpoints/   # REST endpoints (thin controllers)
├── services/               # Async business logic (main logic layer)
├── repositories/           # Complex database queries
├── models/                 # SQLAlchemy ORM models
├── schemas/                # Pydantic request/response validation
├── core/                   # Config, auth, database, exceptions, logging
└── middleware/             # Rate limiting, security headers
```

### Key Patterns

**Async-First**: All database operations and services use `async/await`. Services inject `AsyncSession` via FastAPI dependencies.

**Authentication Flow**: Supabase Auth (phone + password) → JWT token → `get_current_user` dependency → local user sync

**Geospatial Search**: PostGIS `ST_DWithin` for radius-based property search, `ST_Distance` for sorting by proximity.

**Full-Text Search**: PostgreSQL `ts_vector` column (`__ts_vector__`) on properties table.

**Semantic Search**: Hybrid vector + text scoring via `property_embeddings` table (pgvector).

### Service Layer Pattern
```python
class PropertyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_properties(self, filters: dict) -> List[Property]:
        # Business logic here
```

### Dependency Injection
```python
@router.get("/properties/")
async def get_properties(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    return await property_service.search(db, current_user)
```

## Key Files

| Purpose | Location |
|---------|----------|
| App factory | `app/factory.py` |
| Main entry | `app/main.py` |
| API router | `app/api/api_v1/api.py` |
| Database config | `app/core/database.py` |
| Auth logic | `app/core/auth.py` |
| Custom exceptions | `app/core/exceptions.py` |
| Settings | `app/core/config.py` |
| Migrations | `supabase/migrations/` |

## Coding Conventions

- **Python 3.10+**, FastAPI, SQLAlchemy 2.x async, Pydantic v2
- **snake_case** for modules/functions/variables; **PascalCase** for classes
- Full type hints everywhere
- Custom exceptions from `app/core/exceptions.py` (e.g., `UserNotFoundException`)
- Pydantic schemas with `Config.from_attributes = True` for ORM mode
- Use `Optional[]` for nullable fields, avoid `Union[]`
- Validation with `@field_validator` decorators

## Database Models

**Core entities**: User, Property, Agent, Booking, Visit, UserSwipe, Amenity

**Property Management entities**: Lease, RentalApplication, RentCharge, RentPayment, Expense, MaintenanceRequest, Document, Inspection

**Key relationships**:
- User → Properties (as owner), Swipes, Visits, Bookings
- Property → Images, Amenities (M2M via PropertyAmenity), Visits, Bookings
- Agent → User (1:1), Visits
- Property (managed) → Leases, Tenants, Rent, Maintenance, Documents

**Enums** (in `app/models/enums.py`):
- PropertyType: house, apartment, builder_floor, room
- PropertyPurpose: buy, rent, short_stay
- BookingStatus: pending, confirmed, checked_in, checked_out, cancelled, completed
- VisitStatus: scheduled, confirmed, completed, cancelled, rescheduled

## Security

- Supabase JWT auth via `get_current_user` dependency
- Phone as primary identifier
- Role-based access: user, agent, admin
- Rate limiting: 100 req/min global, 5 req/min for auth endpoints
- Input validation via Pydantic schemas

## API Documentation

When running locally:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI YAML: http://localhost:8000/api/v1/openapi.yaml
- Health: http://localhost:8000/health

## MCP Server

360Ghar exposes Model Context Protocol (MCP) servers for AI-powered integrations with OAuth 2.1 authentication (Supabase JWT).

### Server Architecture

| Endpoint | Server | Purpose |
|----------|--------|---------|
| `/mcp` | User MCP | End-user tools for owners, tenants, and regular users |
| `/mcp-admin` | Admin MCP | Administrative tools for agents and platform admins |

### User MCP Tools (`/mcp`)

**Owner Tools** (prefix: `owner.*`):
- `owner.properties.list` - List owned properties
- `owner.properties.create` - Create new property listing
- `owner.properties.get` - Get property details
- `owner.properties.update` - Update property
- `owner.properties.toggle_availability` - Toggle availability status

**Tenant Tools** (prefix: `tenant.*`):
- `tenant.lease.current` - View current lease
- `tenant.rent.history` - View rent payment history
- `tenant.maintenance.create` - Submit maintenance request
- `tenant.maintenance.list` - List maintenance requests

**Booking Tools** (prefix: `bookings.*`):
- `bookings.create` - Book a property
- `bookings.list` - List user bookings
- `bookings.get` - Get booking details
- `bookings.cancel` - Cancel a booking
- `bookings.check_availability` - Check property availability
- `bookings.get_pricing` - Get pricing information

### Admin MCP Tools (`/mcp-admin`)

**Agent Tools** (prefix: `agent.*`):
- `agent.properties.list` - List properties in agent's portfolio
- `agent.properties.get` - Get detailed property info
- `agent.properties.create_for_owner` - Create property for an owner
- `agent.properties.verify` - Verify/approve property listing
- `agent.leases.list` - List all leases
- `agent.leases.create` - Create new lease agreement
- `agent.leases.terminate` - Terminate a lease
- `agent.rent.list_due` - List overdue rent payments
- `agent.rent.record_payment` - Record rent payment
- `agent.maintenance.list` - List maintenance requests
- `agent.maintenance.update_status` - Update maintenance status
- `agent.bookings.list_all` - List all bookings
- `agent.bookings.update_status` - Update booking status
- `agent.dashboard.overview` - Get dashboard metrics

**Admin Tools** (prefix: `admin.*`):
- `admin.system.status` - System health and statistics

### MCP Client Configuration

For end-user applications:
```json
{
  "mcpServers": {
    "ghar360": {
      "transport": "http",
      "url": "https://api.360ghar.com/mcp"
    }
  }
}
```

For agent/admin applications:
```json
{
  "mcpServers": {
    "ghar360-admin": {
      "transport": "http",
      "url": "https://api.360ghar.com/mcp-admin"
    }
  }
}
```

### Key MCP Files

| Purpose | Location |
|---------|----------|
| User MCP server | `app/mcp/user_server.py` |
| Admin MCP server | `app/mcp/admin_server.py` |
| Shared utilities | `app/mcp/utils.py` |
| Validation schemas | `app/mcp/validation.py` |
| Auth provider | `app/mcp/auth_provider.py` |
| Authorization | `app/services/pm_authz.py` |
