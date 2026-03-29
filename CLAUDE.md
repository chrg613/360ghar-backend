# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Platform Overview

360 Ghar is a unified real estate platform with five integrated modules:

- **360 Ghar Core**: Real estate marketplace for buying and renting properties with swipe-based discovery, property visits, and agent coordination (`/api/v1/properties`, `/swipes`, `/visits`, `/agents`)
- **360 Stays**: Short-stay booking platform for hotels, vacation rentals, and temporary accommodations (`/api/v1/bookings`)
- **Property Management**: Comprehensive property management system for landlords and property managers (`/api/v1/pm/*`)
- **360 Virtual Tours**: Immersive 360° property tour platform with AI-powered hotspot generation and scene management (`/api/v1/tours`)
- **360 Data Hub**: Real estate data aggregation with bank auctions, circle rates, court auctions, gazette, jamabandi, RERA projects/complaints, zoning, and neighbourhood data (`/api/v1/data-hub`)

## Build and Development Commands

### Running the API
```bash
uv run python run.py                               # Using uv (recommended)
python run.py                                      # Direct Python
fastapi dev app/main.py --host 0.0.0.0 --port 8000 # Hot reload (FastAPI CLI)
```

> **Note:** This project uses `uv` for dependency management. The `pyproject.toml` includes `[tool.setuptools.packages.find]` configuration to prevent "Multiple top-level packages discovered" errors during the build.

### Testing
```bash
uv run pytest tests/ -v                      # All tests (using uv)
pytest tests/ -v                              # All tests
pytest tests/test_user_service.py -v         # Specific file
pytest tests/ -k "user" -v                   # By keyword
pytest tests/test_file.py::test_func -v      # Single test
pytest tests/ --cov=app --cov-report=html    # With coverage
```

### Data Population
```bash
# Using uv (recommended)
uv run python populate_data/load_comprehensive_data.py          # Full dataset (~300 properties)
uv run python populate_data/load_comprehensive_data.py --quick  # Quick load (~51 properties)
uv run python populate_data/load_comprehensive_data.py --clear  # Clear first, then load

# Or with PYTHONPATH
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

### Docker
```bash
docker-compose up -d           # Start PostGIS 15, Redis 7, and API (hypercorn)
docker-compose up -d db redis  # Start only database services for local dev
```

### Environment Configuration
Copy `.env.example` to `.env` and configure. Key variable groups:
- **Database/Supabase**: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_*_KEY`
- **Redis/Cache**: `REDIS_URL`
- **AI Providers**: `PERPLEXITY_API_KEY`, `GLM_API_KEY`, `GOOGLE_API_KEY`
- **Notifications**: `EMAIL_*`, `SMS_*`, `ENABLE_NOTIF_SCHEDULER`
- **Vector Search**: `VECTOR_SYNC_ENABLED`, `GEMINI_EMBED_MODEL`
- **Blog Auto-Publish**: `AUTO_BLOG_ENABLED`, `AUTO_BLOG_CRON`

### CI/CD Pipeline
GitHub Actions (`.github/workflows/tests.yml`) runs on push/PR to `main`/`develop`:
1. **docs-contracts** — Validates `docs/repo-contract.json` inventory against actual files (`scripts/validate_docs_contracts.py`)
2. **test** — PostGIS + Redis services, `pytest` with `--cov-fail-under=90`, Codecov upload
3. **lint** — `ruff check app/` and `mypy app/`

### Deployment
- **Railway**: `railway.toml` with healthcheck on `/health`, `ON_FAILURE` restart policy
- **Docker**: `Dockerfile` uses `python:3.12-slim` with `python run.py` entry point

## Architecture Overview

### Layered Structure
```
app/
├── api/
│   ├── api_v1/endpoints/   # REST endpoints (thin controllers)
│   ├── api_v1/dependencies/ # Shared auth dependencies
│   └── share.py            # Social share preview endpoints
├── services/               # Async business logic (main logic layer)
│   ├── ai/                 # AI service providers (vastu, gemini, glm)
│   ├── ai_agent/           # AI agent orchestration (tool bridge, conversation store)
│   ├── blog_service/       # Blog content generation
│   └── data_hub/           # Data hub scrapers (bank auctions, circle rates, RERA, etc.)
├── repositories/           # Complex database queries (PropertyRepository, BaseRepository)
├── models/                 # SQLAlchemy ORM models
├── schemas/                # Pydantic request/response validation
├── mcp/                    # MCP servers (user_server, admin_server, chatgpt widgets)
├── core/                   # Config, auth, database, exceptions, logging, websocket
│   └── cache/              # Cache subsystem (memory + Redis backends, decorators)
├── middleware/             # Rate limiting, security headers, trailing slash
├── utils/                  # Shared utilities (distance, validators)
└── vector/                 # Vector embedding store, sync, backfill (pgvector)
```

### Key Patterns

**Async-First**: All database operations and services use `async/await`. Services inject `AsyncSession` via FastAPI dependencies.

**Authentication Flow**: Client authenticates directly with Supabase Auth → bearer access token → `get_current_user` dependency verifies JWT → local user sync

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
| Cache subsystem | `app/core/cache/` |
| Migrations | `supabase/migrations/` |
| Vector embeddings | `app/vector/` |
| Shared utilities | `app/utils/` |
| Data hub scrapers | `app/services/data_hub/` |
| Data hub scheduler | `app/services/data_hub_scheduler.py` |
| AI agent orchestration | `app/services/ai_agent/` |
| Blog auto-publish | `app/services/blog_auto_publish.py`, `app/services/blog_auto_publish_scheduler.py` |
| Notification dispatcher | `app/services/notification_dispatcher.py` |
| Notification scheduler | `app/services/notification_scheduler.py` |
| Vector sync scheduler | `app/services/vector_sync_scheduler.py` |
| Vastu AI analyzer | `app/services/ai/vastu/analyzer.py` |
| AI agent chat | `app/services/agent.py` (agent chat endpoint) |
| Tour AI processing | `app/services/tour_ai.py` |
| Email service | `app/services/email.py` |
| SMS service | `app/services/sms.py` |
| Storage service | `app/services/storage.py` |
| Social share previews | `app/api/share.py` |
| Data hub model | `app/models/data_hub.py` |
| Docs contract validator | `scripts/validate_docs_contracts.py` |

**Background schedulers** (wired in `app/factory.py` startup):
- Blog auto-publish scheduler (`app/services/blog_auto_publish_scheduler.py`)
- Notification scheduler (`app/services/notification_scheduler.py`)
- Vector sync scheduler (`app/services/vector_sync_scheduler.py`)
- Data hub scheduler (`app/services/data_hub_scheduler.py`)

## Coding Conventions

- **Python 3.10+**, FastAPI, SQLAlchemy 2.x async, Pydantic v2
- **snake_case** for modules/functions/variables; **PascalCase** for classes
- Full type hints everywhere
- Custom exceptions from `app/core/exceptions.py` (e.g., `UserNotFoundException`)
- Pydantic schemas with `Config.from_attributes = True` for ORM mode
- Use `Optional[]` for nullable fields, avoid `Union[]`
- Validation with `@field_validator` decorators

## Dependency & Documentation Policy

- **Always use latest stable versions**: When adding or upgrading dependencies, research the latest stable release. Never pin to outdated versions based on cached knowledge.
- **Research before integrating**: Before implementing any 3rd party integration (APIs, SDKs, libraries), look up the current official documentation. Do not rely on training data alone — docs change frequently.
- **Use Context7 MCP or web search**: Use the `context7` MCP tools (`resolve-library-id` + `query-docs`) or `WebSearch`/`WebFetch` to retrieve up-to-date documentation and code examples for any library or service being used.
- **Verify compatibility**: Confirm that new dependencies are compatible with the project's Python 3.10+ requirement and existing stack (FastAPI, SQLAlchemy 2.x async, Pydantic v2).
- **Check changelogs for breaking changes**: When upgrading a dependency, review its changelog/migration guide to avoid breaking changes.

## Database Models

**Core entities**: User, Property, Agent, AgentInteraction, Booking, Visit, UserSwipe, Amenity

**Blog entities**: BlogPost, BlogCategory, BlogTag, BlogPostCategory, BlogPostTag

**360 Virtual Tour entities**: Tour, Scene, Hotspot, TourAnalyticsEvent, AIJob, MediaFile, FloorPlan, TourBranding, CustomDomain, VideoMetadata

**Property Management entities**: Lease, RentalApplication, RentalApplicationForm, RentCharge, RentPayment, Expense, MaintenanceRequest, Document, InspectionChecklist

**AI entities**: AIConversation, AIConversationMessage

**Data Hub entities**: BankAuction, CircleRate, CourtAuction, Gazette, Jamabandi, RERAProject, RERAComplaint, Zoning, Neighbourhood, BankRate, DataHubAlert

**Key relationships**:
- User → Properties (as owner), Swipes, Visits, Bookings, Tours
- Property → Images, Amenities (M2M via PropertyAmenity), Visits, Bookings
- Agent → Users (1:many), Visits, AgentInteractions
- Property (managed) → Leases, Tenants, Rent, Maintenance, Documents

**Enums** (in `app/models/enums.py`):
- PropertyType: house, apartment, builder_floor, room, villa, plot, condo, penthouse, studio, loft, pg, flatmate, office, shop, warehouse
- PropertyPurpose: buy, rent, short_stay
- BookingStatus: pending, confirmed, checked_in, checked_out, cancelled, completed
- VisitStatus: scheduled, confirmed, completed, cancelled, rescheduled
- LeaseStatus: draft, active, expired, terminated
- MaintenanceCategory, MaintenanceUrgency, MaintenanceRequestStatus, WorkOrderStatus
- TourStatus, SceneType, HotspotType, AIJobStatus
- DocumentType, InspectionType, TenantStatus, ExpenseCategory
- UserRole: user, agent, admin
- AgentType, ExperienceLevel

## Test Structure

```
tests/
├── api/                    # Endpoint integration tests
├── unit/
│   ├── core/               # Auth, config unit tests
│   ├── models/             # Model/enum tests
│   ├── schemas/            # Schema validation tests
│   ├── services/           # Service layer unit tests
│   └── mcp/                # MCP server tests
├── integration/            # Full-stack DB integration tests (PostGIS, FTS)
├── e2e/                    # End-to-end flow tests
├── pm/                     # Property management tests
├── middleware/             # Middleware tests
└── fixtures/               # Shared fixtures (auth, factories, mocks, data)
```

Run with coverage: `pytest tests/ --cov=app --cov-report=html`
Dev dependencies (pytest, ruff, mypy) are in the `dev` optional group: `pip install ".[dev]"`

## Security

- Supabase JWT auth via `get_current_user` dependency
- Phone as primary identifier
- Role-based access: user, agent, admin
- Backend does not provide `/api/v1/auth/*` user-session endpoints; clients own login/refresh/logout via Supabase SDK
- Rate limiting: 100 req/min global
- Input validation via Pydantic schemas

## API Documentation

When running locally:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI YAML: http://localhost:8000/api/v1/openapi.yaml
- Health: http://localhost:8000/health

## MCP Server

360Ghar exposes Model Context Protocol (MCP) servers compatible with **any MCP client** — ChatGPT Apps, Claude Desktop, Cursor, VS Code Copilot, Gemini, MCPJam, and all MCP-compliant hosts. Authentication uses OAuth 2.1 with PKCE.

### Server Architecture

| Endpoint | Server | Purpose |
|----------|--------|---------|
| `/mcp` | User MCP (`ghar360-user`) | End-user tools for owners, tenants, property seekers, and guests |
| `/mcp-admin` | Admin MCP (`ghar360-admin`) | Administrative tools for agents and platform admins |

Both servers use `AppsSDKFastMCP` (extends FastMCP 3.0.1) with OAuth 2.1 + PKCE and share authorization endpoints at `/mcp/oauth/*`.

### Protocol and Transport

- **MCP protocol version**: `2025-11-25`
- **Transport**: Streamable HTTP (stateless, binary JSON-RPC over HTTP) — not SSE
- **Framework**: FastMCP 3.0.1 via `AppsSDKFastMCP` (`app/mcp/apps_sdk.py`)
- **Experimental capability**: `io.modelcontextprotocol/ui` advertised in initialization options — signals support for interactive HTML widget resources to all MCP hosts

### Universal Client Support

A single server URL serves all MCP clients with no per-client adapters:

- **Dual-metadata strategy**: `build_widget_tool_meta()` in `app/mcp/apps_sdk.py` emits both standard MCP keys (`ui.resourceUri`, `ui.visibility`) and OpenAI-compatible aliases (`openai/outputTemplate`, `openai/widgetAccessible`, `openai/toolInvocation/*`). Widget resources are similarly registered with both standard and OpenAI metadata keys.
- **Bridge runtime detection**: The widget bridge (`chatgpt-widgets/src/utils/bridge.ts`) detects the host at module load — `window.openai` present means OpenAI host; iframe (`window.parent !== window`) means MCP Apps host (JSON-RPC postMessage); else standalone. All widgets work without per-widget changes.
- **OAuth discovery**: Full RFC 9728 / RFC 8414 well-known metadata enables any OAuth 2.1 client to discover the authorization server and register dynamically via `/mcp/oauth/register`.

### User MCP Tools (`/mcp`)

**Discovery Tools** (prefix: `discovery_*`):
- `discovery_search` - Search properties with filters (guest)
- `discovery_property_get` - Get full property details (guest)
- `discovery_feed` - Get discovery feed for swiping (guest)
- `discovery_amenities` - List available amenities (guest)
- `discovery_swipe` - Record like/pass on property (auth)
- `discovery_shortlist` - Get liked properties (auth)
- `discovery_recommendations` - Get AI recommendations (auth)

**Visit Tools** (prefix: `visits_*`):
- `visits_schedule` - Schedule a property visit (auth)
- `visits_list` - List user's visits (auth)
- `visits_get` - Get visit details (auth)
- `visits_cancel` - Cancel a scheduled visit (auth)

**Owner Tools** (prefix: `owner_*`):
- `owner_properties_list` - List owned properties
- `owner_properties_create` - Create new property listing
- `owner_properties_get` - Get property details
- `owner_properties_update` - Update property
- `owner_properties_toggle_availability` - Toggle availability status
- `owner_dashboard_overview` - Get portfolio dashboard with analytics
- `owner_leases_list` - List property leases
- `owner_leases_get` - Get lease details
- `owner_leases_terminate` - Terminate a lease
- `owner_rent_status` - View rent collection status
- `owner_rent_record_payment` - Record a rent payment
- `owner_rent_history` - View payment history
- `owner_maintenance_list` - List maintenance requests
- `owner_maintenance_update` - Update maintenance request status

**Tenant Tools** (prefix: `tenant_*`):
- `tenant_lease_current` - View current lease
- `tenant_rent_dues` - View outstanding rent dues
- `tenant_rent_history` - View rent payment history
- `tenant_maintenance_create` - Submit maintenance request
- `tenant_maintenance_list` - List maintenance requests

**Booking Tools** (prefix: `bookings_*`):
- `bookings_create` - Book a property
- `bookings_list` - List user bookings
- `bookings_get` - Get booking details
- `bookings_cancel` - Cancel a booking
- `bookings_check_availability` - Check property availability
- `bookings_get_pricing` - Get pricing information

### Admin MCP Tools (`/mcp-admin`)

**Agent Tools** (prefix: `agent_*`):
- `agent_properties_list` - List properties in agent's portfolio
- `agent_properties_get` - Get detailed property info
- `agent_properties_create_for_owner` - Create property for an owner
- `agent_properties_verify` - Verify/approve property listing
- `agent_leases_list` - List all leases
- `agent_leases_create` - Create new lease agreement
- `agent_leases_terminate` - Terminate a lease
- `agent_rent_list_due` - List overdue rent payments
- `agent_rent_record_payment` - Record rent payment
- `agent_maintenance_list` - List maintenance requests
- `agent_maintenance_update_status` - Update maintenance status
- `agent_bookings_list_all` - List all bookings
- `agent_bookings_update_status` - Update booking status
- `agent_dashboard_overview` - Get dashboard metrics

**Admin Tools** (prefix: `admin_*`):
- `admin_system_status` - System health and statistics

### MCP Client Configuration

All clients connect to the same server URL. Configuration format varies by client:

**Generic Streamable HTTP** (any MCP client):
```json
{
  "mcpServers": {
    "360ghar": {
      "transport": "http",
      "url": "https://api.360ghar.com/mcp"
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "360ghar": {
      "type": "streamable-http",
      "url": "https://api.360ghar.com/mcp"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "360ghar": {
      "url": "https://api.360ghar.com/mcp",
      "transport": "streamable-http"
    }
  }
}
```

**VS Code Copilot** (`.vscode/mcp.json`):
```json
{
  "servers": {
    "360ghar": {
      "url": "https://api.360ghar.com/mcp",
      "type": "http"
    }
  }
}
```

**ChatGPT Apps**: Settings > Apps & Connectors > Advanced, URL: `https://api.360ghar.com/mcp`

> For agent/admin access, use `https://api.360ghar.com/mcp-admin` as the URL. Client config formats change — check your client's documentation for the current format.

### Generative UI (Widgets)

11 React widgets bundled as standalone HTML files in `chatgpt-widgets/dist/`, registered as MCP resources with MIME type `text/html;profile=mcp-app`:

| Widget | Linked Tools |
|--------|-------------|
| PropertySearchWidget | `discovery_search`, `guest_property_search`, `guest_property_recommendations` |
| PropertyDetailsWidget | `discovery_property_get`, `guest_property_details`, `owner_properties_get`, `agent_properties_get` |
| PropertySwipeWidget | `discovery_feed` |
| VisitSchedulerWidget | `visits_schedule`, `bookings_get` |
| VisitListWidget | `visits_list`, `bookings_list`, `agent_bookings_list_all` |
| LeaseDetailsWidget | `tenant_lease_current` |
| MaintenanceWidget | `tenant_maintenance_list`, `tenant_maintenance_create`, `agent_maintenance_list` |
| OwnerDashboardWidget | `owner_properties_list`, `owner_dashboard_overview`, `agent_properties_list`, `agent_dashboard_overview` |
| LeaseManagementWidget | `owner_leases_list`, `owner_leases_get`, `agent_leases_list` |
| RentCollectionWidget | `owner_rent_status`, `owner_rent_record_payment`, `owner_rent_history`, `agent_rent_list_due`, `agent_rent_record_payment` |
| TenantRentWidget | `tenant_rent_dues`, `tenant_rent_history` |

**Bridge protocol**: `chatgpt-widgets/src/utils/bridge.ts` provides unified React hooks (`useToolOutput`, `useCallTool`, `useSendMessage`, `useTheme`, `useWidgetState`) that work identically on OpenAI and MCP Apps hosts. MCP Apps protocol version `2026-01-26` with JSON-RPC 2.0 over postMessage (`ui/initialize`, `ui/notifications/*`, `tools/call`, `ui/message`, auto-resize).

**Theme support**: Light/dark mode propagated from host context on all MCP hosts.

**Content-hash versioning**: Widget URIs include `?v=<content_hash>` for cache busting, computed at registration time.

**Widget-to-tool mapping**: Defined in `WIDGETS` dict in `app/mcp/chatgpt/__init__.py`. `get_widget_for_tool()` resolves tool names to versioned widget URIs.

### Feature Support Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| Tools | Supported | 40+ tools across user and admin servers |
| Resources (Widgets) | Supported | 11 HTML widget resources via `io.modelcontextprotocol/ui` |
| OAuth 2.1 + PKCE | Supported | Full RFC 6749/7636/7591/8414/8707/9728 |
| Generative UI | Supported | Interactive HTML widgets on all MCP hosts |
| Tool annotations | Supported | `readOnlyHint`, `openWorldHint`, `destructiveHint`, `securitySchemes` |
| Structured output | Supported | `structuredContent` in all tool results |
| Elicitation | Not yet | Mid-tool user questions (MCP protocol feature) |
| Sampling | Not yet | LLM callbacks to client |
| Server notifications | Not yet | Proactive server-to-client notifications |
| Progress tokens | Not yet | Long-running tool progress reporting |

### Apps SDK Compliance

The MCP servers are compatible with the OpenAI Apps SDK and the MCP Apps standard (SEP-1865) from a single server:

- **Widget MIME type**: Use `RESOURCE_MIME_TYPE` from `app/mcp/apps_sdk.py` (`text/html;profile=mcp-app`) when registering widget resources
- **Tool annotations**: Every tool must include `readOnlyHint`, `openWorldHint`, and `destructiveHint` in its `annotations` dict
- **Security schemes**: Every tool must include `securitySchemes` (use `MCP_SECURITY_SCHEMES_MIXED` for guest-accessible tools, `MCP_SECURITY_SCHEMES_OAUTH2_ONLY` for auth-required tools)
- **Dual metadata**: Use `build_widget_tool_meta()` to emit both standard `ui.*` keys and OpenAI `openai/*` alias keys — ensures widgets render on all MCP hosts
- **Widget URI in responses**: Pass `widget_uri=get_widget_for_tool("tool_name")` to `format_chatgpt_response()` for widget-linked tools
- **Response format**: Return `AppsSDKToolResult` with `content` (text summary), `structuredContent` (JSON data), and `_meta` (widget metadata) — compatible with all MCP hosts
- **Auth challenges**: Use `raise_auth_required()` (not raw `AuthRequiredError`) to ensure the challenge includes `resource_metadata` URL and triggers the host's OAuth UI
- **Widget versioning**: Widget URIs include content hash (`?v=...`) for cache busting, computed at registration time

### Key MCP Files

| Purpose | Location |
|---------|----------|
| User MCP server | `app/mcp/user_server.py` |
| Admin MCP server | `app/mcp/admin_server.py` |
| Apps SDK helpers | `app/mcp/apps_sdk.py` |
| Multi-client tools | `app/mcp/chatgpt/` |
| Response formatters | `app/mcp/chatgpt/response_formatter.py` |
| Widget registry | `app/mcp/chatgpt/__init__.py` |
| Widget bridge (multi-host) | `chatgpt-widgets/src/utils/bridge.ts` |
| Widget theme support | `chatgpt-widgets/src/utils/theme.ts` |
| Built widget HTML | `chatgpt-widgets/dist/` |
| Shared utilities | `app/mcp/utils.py` |
| Validation schemas | `app/mcp/validation.py` |
| MCP error helpers | `app/mcp/errors.py` |
| Auth provider | `app/mcp/auth_provider.py` |
| OAuth endpoints | `app/api/api_v1/endpoints/oauth.py` |
| Authorization | `app/services/pm_authz.py` |
