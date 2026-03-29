# 360Ghar MCP Widgets

This directory contains the interactive widget system for 360Ghar's MCP servers, enabling rich UI experiences across **all MCP-compatible hosts** — ChatGPT Apps, Claude Desktop, Cursor, VS Code Copilot, Gemini, MCPJam, and any MCP-compliant client.

## Architecture

The widgets are built on the **Model Context Protocol (MCP)** standard and consist of:

1. **MCP Server** (`/mcp`) - Exposes tools that any MCP client can call
2. **Widget UI** (`chatgpt-widgets/`) - React components rendered in host iframes
3. **Unified Bridge** - Runtime-detected API layer that works on all hosts

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   ChatGPT   │  │   Claude    │  │   Cursor    │  │  VS Code    │
│   (OpenAI)  │  │  Desktop    │  │             │  │  Copilot    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                                │
                                ▼
                  ┌─────────────────────────┐
                  │    MCP Server (/mcp)     │────▶ 360Ghar API
                  │  (AppsSDKFastMCP)        │◀──── (Backend)
                  └───────────┬─────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │  Widget iframe (HTML)    │
                  │  Unified Bridge detects  │
                  │  host at runtime         │
                  └─────────────────────────┘
```

## Features

### For Property Seekers (Guest + Authenticated)
- **Property Search** - Search by location, filters, price range
- **Property Details** - View full property information with images
- **Discovery Feed** - Swipe-based property discovery (like/pass)
- **Visit Scheduling** - Schedule property visits (requires auth)
- **Shortlist** - Save and view liked properties (requires auth)

### For Tenants
- **Lease Information** - View current lease details
- **Rent Dues** - View outstanding rent and payment due dates
- **Rent History** - Track rent payments
- **Maintenance Requests** - Submit and track maintenance issues

### For Property Owners
- **Property Dashboard** - Overview of owned properties with analytics
- **Lease Management** - View, manage, and terminate leases
- **Rent Collection** - Track payments, record transactions, view overdue
- **Maintenance Tracking** - View and update maintenance requests
- **Occupancy Stats** - Track occupied vs vacant units

## Directory Structure

```
app/mcp/chatgpt/
├── __init__.py           # Module initialization & widget registration
├── discovery_tools.py    # Property search, details, swipe tools
├── visit_tools.py        # Visit scheduling tools
├── pm_tools.py           # Property management tools (leases, rent, maintenance)
├── response_formatter.py # Response formatting for all MCP hosts
└── validation.py         # Pydantic schemas for tool inputs

chatgpt-widgets/
├── package.json          # npm configuration
├── tsconfig.json         # TypeScript configuration
├── scripts/
│   └── build-widgets.js  # Build script for HTML bundles
├── src/
│   ├── types/
│   │   └── openai.d.ts   # window.openai TypeScript definitions
│   ├── utils/
│   │   ├── bridge.ts     # Unified bridge hooks (works on all MCP hosts)
│   │   └── theme.ts      # Theme colors for dark/light mode
│   ├── components/
│   │   ├── common/       # Reusable components (Button, Card)
│   │   └── property/     # Property-specific components
│   └── widgets/          # Widget entry points (11 total)
│       ├── PropertySearchWidget.tsx
│       ├── PropertyDetailsWidget.tsx
│       ├── PropertySwipeWidget.tsx
│       ├── VisitSchedulerWidget.tsx
│       ├── VisitListWidget.tsx
│       ├── LeaseDetailsWidget.tsx
│       ├── MaintenanceWidget.tsx
│       ├── OwnerDashboardWidget.tsx
│       ├── LeaseManagementWidget.tsx    # Owner lease management
│       ├── RentCollectionWidget.tsx     # Owner rent tracking
│       └── TenantRentWidget.tsx         # Tenant rent dues
└── dist/                 # Built HTML bundles (11 files)
```

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Building Widgets

```bash
cd chatgpt-widgets

# Install dependencies
npm install

# Build all widgets
npm run build

# Watch mode for development
npm run build:watch
```

### Testing Locally

1. Start the FastAPI backend:
   ```bash
   fastapi dev app/main.py --host 0.0.0.0 --port 8000
   ```

2. Use ngrok to expose the server:
   ```bash
   ngrok http 8000
   ```

3. Test with MCP Inspector (universal testing tool):
   ```bash
   npx @mcpjam/inspector --url https://your-ngrok-url.ngrok.io/mcp --oauth --verbose
   ```

4. Connect from your preferred client:
   - **ChatGPT**: Settings > Apps & Connectors > Advanced, add URL + `/mcp`
   - **Claude Desktop**: Add to `claude_desktop_config.json` with `type: "streamable-http"`
   - **Cursor**: Add to `.cursor/mcp.json` with `transport: "streamable-http"`
   - **VS Code Copilot**: Add to `.vscode/mcp.json` with `type: "http"`

## OAuth Compatibility

The MCP server supports standards-based OAuth for multi-client compatibility:

- Single user MCP endpoint: `/mcp`
- Admin MCP endpoint: `/mcp-admin`
- Dynamic client registration: `/mcp/oauth/register`
- Authorization code + PKCE: `/mcp/oauth/authorize`, `/mcp/oauth/token`
- Token revocation: `/mcp/oauth/revoke`
- Discovery metadata:
  - `/.well-known/oauth-protected-resource`
  - `/.well-known/oauth-protected-resource/mcp`
  - `/.well-known/oauth-protected-resource/mcp-admin`
  - `/.well-known/oauth-authorization-server/mcp/oauth`

## Tool Reference

### Discovery Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `discovery.search` | Search properties with filters | No |
| `discovery.property.get` | Get full property details | No |
| `discovery.feed` | Get discovery feed for swiping | No |
| `discovery.amenities` | List available amenities | No |
| `discovery.swipe` | Record like/pass on property | Yes |
| `discovery.shortlist` | Get liked properties | Yes |
| `discovery.recommendations` | Get AI recommendations | Yes |

### Visit Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `visits.schedule` | Schedule a property visit | Yes |
| `visits.list` | List user's visits | Yes |
| `visits.get` | Get visit details | Yes |
| `visits.cancel` | Cancel a scheduled visit | Yes |

### Tenant Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `tenant.lease.current` | Get current lease | Yes |
| `tenant.rent.dues` | View outstanding rent | Yes |
| `tenant.rent.history` | Get rent payment history | Yes |
| `tenant.maintenance.create` | Submit maintenance request | Yes |
| `tenant.maintenance.list` | List maintenance requests | Yes |

### Owner Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `owner.properties.list` | List owned properties | Yes |
| `owner.properties.create` | Create new listing | Yes |
| `owner.properties.get` | Get property details | Yes |
| `owner.properties.update` | Update property | Yes |
| `owner.dashboard.overview` | Get portfolio dashboard | Yes |
| `owner.leases.list` | List leases for properties | Yes |
| `owner.leases.get` | Get lease details | Yes |
| `owner.leases.terminate` | Terminate a lease | Yes |
| `owner.rent.status` | View rent collection status | Yes |
| `owner.rent.record_payment` | Record a rent payment | Yes |
| `owner.rent.history` | View payment history | Yes |
| `owner.maintenance.list` | List maintenance requests | Yes |
| `owner.maintenance.update` | Update maintenance status | Yes |

## Widget Development

### Using the Unified Widget Bridge

The bridge (`src/utils/bridge.ts`) provides identical React hooks regardless of the host runtime. It auto-detects the host at module load — no per-widget configuration needed.

```tsx
import { useToolOutput, useCallTool, useSendMessage } from '../utils/bridge';

function MyWidget() {
  // Get tool output data — works on all MCP hosts
  const data = useToolOutput<MyDataType>();

  // Call other tools — uses window.openai on ChatGPT, JSON-RPC on other hosts
  const callTool = useCallTool();
  await callTool('discovery.search', { city: 'Mumbai' });

  // Send follow-up messages — adapts to host protocol
  const sendMessage = useSendMessage();
  sendMessage('Show me details for property 123');
}
```

**Available hooks** (all work identically across hosts):

| Hook | OpenAI Host | MCP Apps Host |
|------|-------------|---------------|
| `useToolOutput()` | `window.openai.toolOutput` | JSON-RPC `ui/notifications/tool-result` |
| `useToolMeta()` | `window.openai.toolResponseMetadata` | JSON-RPC `_meta` field |
| `useWidgetState()` | `window.openai.setWidgetState()` | `localStorage` persistence |
| `useTheme()` | `window.openai.theme` | `ui/notifications/host-context-changed` |
| `useCallTool()` | `window.openai.callTool()` | JSON-RPC `tools/call` |
| `useSendMessage()` | `window.openai.sendFollowUpMessage()` | JSON-RPC `ui/message` |
| `useOpenExternal()` | `window.openai.openExternal()` | `window.open()` fallback |

### Theme Support

Themes work on all MCP Apps hosts, not just ChatGPT:

```tsx
import { useThemeColors } from '../utils/theme';

function MyComponent() {
  const colors = useThemeColors();

  return (
    <div style={{
      backgroundColor: colors.background,
      color: colors.text
    }}>
      Content
    </div>
  );
}
```

## Deployment

1. Build widgets: `npm run build` in `chatgpt-widgets/`
2. Deploy backend to production
3. Ensure CORS allows all MCP client origins (`chatgpt.com`, `chat.openai.com`, and any MCP host domains)
4. Configure MCP endpoint at `https://api.360ghar.com/mcp`

## MCP Client Configuration

All clients connect to the same server URL. For end users:

**ChatGPT Apps**: Settings > Apps & Connectors > Advanced, URL: `https://api.360ghar.com/mcp`

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

> For agent/admin access, use `https://api.360ghar.com/mcp-admin` as the URL.

## Security Considerations

- All sensitive operations require authentication
- OAuth 2.1 with PKCE for secure token exchange
- CSP headers restrict widget network access
- Never embed secrets in widget responses
- Tool handlers are idempotent (safe for retries)
