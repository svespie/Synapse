# Synapse: Design Document

## Context

Synapse is a greenfield Python CLI application — an MCP (Model Context Protocol) interaction framework for security professionals. Think "Metasploit for MCP servers": a terminal-based REPL where operators connect to multiple MCP servers, enumerate their capabilities, invoke tools, and run security-focused modules. The architecture must support evolution into a full AI red teaming framework without requiring a core rewrite.

**Repo state**: Some files already created by user during planning. Existing `.venv` virtual environment in place.

---

## Architecture: Three-Layer Design

```
 ./synapse                          # Unix-style executable entry point
    │                               # Collects env vars + CLI args via argparse
    ▼                               # No importable main() — __main__ block only
┌─────────────────────────────────────────────────┐
│              Application Entry                  │
│  app/main.py — Synapse class, interface router  │
├─────────────────────────────────────────────────┤
│                  CLI Layer                       │
│  app/cli/repl.py, commands/, formatter.py       │
│  prompt_toolkit + rich                          │
├─────────────────────────────────────────────────┤
│                Module Layer                      │
│  app/modules/base.py, registry.py               │
│  app/modules/enumerate/, audit/, invoke/, recon/ │
├─────────────────────────────────────────────────┤
│                 Core Layer                       │
│  app/core/connection.py, session.py, transport.py│
│  app/core/auth/, config.py, events.py            │
│  app/core/models/                                │
│  Uses: mcp SDK, httpx, pydantic, anyio           │
└─────────────────────────────────────────────────┘
```

**Critical invariant**: `core/` and `modules/` never import from `cli/`. The core library is UI-independent — a web UI, REST API, or test harness can replace `cli/` without touching the engine.

---

## Project Structure

```
Synapse/
├── synapse                         # Executable entry point (no extension, chmod +x)
│                                   # argparse for --verbose and --no-banner only
│                                   # All logic in if __name__ == "__main__": block
├── pyproject.toml                  # Project metadata, dependencies
├── README.md                       # Setup instructions (uv, venv, usage)
├── LICENSE
├── .python-version                 # 3.12
├── .env                            # Secrets only (never committed, in .gitignore)
│
├── app/
│   ├── __init__.py                 # Package version
│   ├── main.py                     # Synapse app class — boots core, selects interface
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── connection.py           # ConnectionManager, ManagedConnection
│   │   ├── session.py              # SessionManager (active session tracking)
│   │   ├── transport.py            # TransportConfig, TransportType, TransportFactory
│   │   ├── config.py               # Config loading: TOML + .env, auto-generate on first run
│   │   ├── events.py               # Async event bus (decouples core from UI)
│   │   ├── errors.py               # Exception hierarchy
│   │   ├── models/                 # Pydantic models, one per domain concept
│   │   │   ├── __init__.py         # Re-exports for convenience
│   │   │   ├── connection.py       # ConnectionInfo, ConnectionState
│   │   │   ├── server.py           # ServerInfo, ServerCapabilities
│   │   │   ├── tools.py            # ToolInfo, ToolResult
│   │   │   ├── resources.py        # ResourceInfo, ResourceContent
│   │   │   ├── prompts.py          # PromptInfo, PromptResult
│   │   │   └── auth.py             # AuthCredentials, AuthConfig
│   │   │
│   │   └── auth/
│   │       ├── __init__.py
│   │       ├── base.py             # AuthProvider protocol, AuthCredentials
│   │       ├── api_key.py          # Bearer token / static API key
│   │       ├── pat.py              # Personal Access Token (env-var backed)
│   │       ├── oauth2.py           # OAuth 2.1 — also handles corporate SSO (AD-backed)
│   │       ├── aws_sso.py          # AWS IAM Identity Center (deferred)
│   │       └── registry.py         # AuthProviderRegistry (entry-point discovery)
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseModule ABC, ModuleOption, ModuleResult, ModuleMetadata
│   │   ├── registry.py             # ModuleRegistry (package scan + entry points)
│   │   ├── enumerate/
│   │   │   ├── __init__.py
│   │   │   ├── tools.py            # List tools across sessions
│   │   │   ├── resources.py        # List resources across sessions
│   │   │   └── prompts.py          # List prompts across sessions
│   │   ├── invoke/
│   │   │   ├── __init__.py
│   │   │   └── tool_call.py        # Direct tool invocation with JSON args
│   │   ├── audit/                  # (deferred — architecture ready)
│   │   │   └── __init__.py
│   │   └── recon/                  # (deferred — architecture ready)
│   │       └── __init__.py
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── repl.py                 # REPL engine (prompt_toolkit + async event loop)
│   │   ├── context.py              # Context stack (stack-based, arbitrary depth)
│   │   ├── completer.py            # Tab completion (context-aware)
│   │   ├── formatter.py            # Rich tables, panels, syntax highlighting
│   │   ├── banner.py               # Banner string constant + display logic
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── base.py             # BaseCommand ABC (strategy pattern)
│   │       ├── registry.py         # CommandRegistry
│   │       ├── global_cmds.py      # help, connect, disconnect, sessions, search, exit
│   │       ├── module_cmds.py      # use, set, unset, show, run, back, info
│   │       └── session_cmds.py     # tools, resources, prompts, call, read (resource by URI)
│   │
│   └── utils/
│       ├── __init__.py
│       └── async_helpers.py        # Async utilities
│
└── tests/
    ├── conftest.py                 # pytest convention: shared test fixtures
    ├── core/
    ├── modules/
    └── cli/
```

### Key structural decisions

- **No `banner.txt`** — banner is a string constant embedded in `app/cli/banner.py`
- **No `configs/` directory** — config auto-generated to `~/.synapse/config.toml` on first run with commented examples
- **No `--config` CLI flag** — app loads from `~/.synapse/config.toml`, fails fast with helpful message if missing
- **`conftest.py`** — this is a pytest-mandated name (not ours to change), it's where shared test fixtures live
- **Tool args are JSON** — MCP protocol uses JSON-RPC 2.0, tool arguments are JSON objects on the wire. The SDK's `tools/call` takes a Python dict which we parse from user-provided JSON. Tool schemas vary per-server so we can't predefine dataclasses for them.

### Entry Point Design

The `./synapse` file is a Unix-style executable script (no `.py` extension):

```python
#!/usr/bin/env python3
"""Synapse - MCP Interaction Framework"""
import argparse
import os
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synapse - MCP Interaction Framework")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--no-banner", action="store_true", help="Skip the ASCII banner")
    parser.add_argument("--proxy", default=None, help="HTTP proxy URL (e.g. http://127.0.0.1:8080 for Burp Suite)")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification (for proxy TLS interception)")
    args = parser.parse_args()

    from app.main import Synapse
    synapse = Synapse(
        verbose=args.verbose,
        show_banner=not args.no_banner,
        proxy_url=args.proxy,
        verify_ssl=not args.no_verify_ssl,
    )
    synapse.run()
```

`app/main.py` contains the `Synapse` class — the application root. It:
1. Loads config from `~/.synapse/config.toml` (fails fast if missing, with guidance on first run)
2. Loads secrets from `.env`
3. Boots core services (ConnectionManager, SessionManager, ModuleRegistry, AuthRegistry, EventBus)
4. Launches the selected interface (CLI REPL for MVP, future: web UI, API server)

---

## Core Components

### Transport Layer (`app/core/transport.py`)

Wraps the MCP Python SDK's transport context managers with a config-driven factory.

- **TransportType**: `STDIO`, `STREAMABLE_HTTP`, `SSE` (StrEnum)
- **TransportConfig**: Pydantic model — validates that STDIO has `command`, HTTP has `url`
- **TransportFactory**: Takes config + optional auth, returns the appropriate MCP SDK async context manager. For HTTP transports, builds a configured `httpx.AsyncClient` with auth headers/certs injected
- **Proxy support**: `httpx.AsyncClient` accepts a `proxy` parameter — enables routing all HTTP MCP traffic through Burp Suite (`127.0.0.1:8080`), mitmproxy, or ZAP for traffic analysis. Configurable globally and per-server in TOML. Optional `verify_ssl = false` for TLS interception with proxy CA certs

### Auth System (`app/core/auth/`)

Pluggable via a `Protocol`:

```python
class AuthProvider(Protocol):
    auth_type: str
    async def get_credentials(self) -> AuthCredentials
    async def refresh(self) -> AuthCredentials
    async def apply_to_client(self, client: httpx.AsyncClient) -> httpx.AsyncClient  # for HTTP
    async def apply_to_env(self, env: dict[str, str]) -> dict[str, str]              # for STDIO
    def is_expired(self) -> bool
```

Two application paths: `apply_to_client()` configures HTTP auth (Bearer tokens, mTLS certs), `apply_to_env()` injects env vars for subprocess-based STDIO servers.

**MVP**: `ApiKeyAuth` (static Bearer token), `PatAuth` (env-var backed token), `OAuth2Auth` (handles corporate SSO — see below)

**Corporate SSO / Active Directory**: This is an OAuth 2.1 authorization code flow where the corporate IdP (Active Directory / Entra ID) is the identity provider. The flow:
1. Client hits the MCP server URL
2. Server returns 401 + OAuth metadata (authorization/token endpoints)
3. Client opens browser for user to authenticate via corporate SSO
4. User authenticates, gets redirected back to a local callback
5. Client receives auth code, exchanges for access token
6. Token used for all subsequent MCP requests

The MCP SDK has built-in support via `OAuthClientProvider`. Our `OAuth2Auth` provider wraps this. This is not a separate "SSO" type — SSO is the identity provider behind the OAuth flow.

**Post-MVP**: AWS SSO, mTLS, OIDC, Kerberos/SPNEGO, HashiCorp Vault, cloud IAM (GCP/Azure)

**Additional auth types**:
| Type | Rationale |
|------|-----------|
| mTLS | Zero-trust enterprise, service meshes |
| OIDC | Okta/Auth0/Azure AD identity layer (distinct token handling from OAuth2) |
| Kerberos/SPNEGO | Active Directory environments (non-OAuth path) |
| HashiCorp Vault | Dynamic secrets from Vault |
| Cloud IAM (GCP/Azure) | Cloud-native MCP server deployments |

### Connection Manager (`app/core/connection.py`)

Owns the lifecycle of individual MCP connections. Each `ManagedConnection` bundles:
- Transport config + auth provider
- MCP `ClientSession` (from SDK)
- Cached `ServerInfo` (discovered tools, resources, prompts)
- `AsyncExitStack` for clean lifecycle management
- User-assigned name/alias + connection state

Key operations: `connect()`, `disconnect()`, `disconnect_all()`, `get()`, `list_connections()`

The `connect()` flow:
1. Create `AsyncExitStack`
2. Wire auth into transport (HTTP client or env vars)
3. Enter transport context manager
4. Create + enter `ClientSession`
5. Call `session.initialize()` (MCP handshake)
6. Enumerate and cache tools/resources/prompts
7. Store `ManagedConnection`, emit event

### Session Manager (`app/core/session.py`)

Sits above ConnectionManager. Tracks the "active session" — which connection commands target by default.

- `active` property -> current `ManagedConnection`
- `switch_to(name_or_id)` -> change active session
- `call_tool()`, `list_tools()`, `list_resources()`, `read_resource()`, etc. — delegate to active or specified session

### Models (`app/core/models/`)

Separated into domain-specific modules:
- `connection.py` — ConnectionInfo, ConnectionState
- `server.py` — ServerInfo, ServerCapabilities
- `tools.py` — ToolInfo, ToolResult
- `resources.py` — ResourceInfo, ResourceContent
- `prompts.py` — PromptInfo, PromptResult
- `auth.py` — AuthCredentials, AuthConfig

`__init__.py` re-exports all models for convenience: `from app.core.models import ServerInfo, ToolResult`

### Event Bus (`app/core/events.py`)

Lightweight async pub/sub. Core emits events (`ConnectionEstablished`, `ToolCallCompleted`, `ModuleCompleted`), CLI subscribes for live output. Decouples core from any specific UI.

---

## Configuration

**Dual config approach**:

- **`.env`** (project root) — secrets only (tokens, API keys). Never committed. Loaded by the app on startup via `python-dotenv`. Referenced by TOML config via `env:VAR_NAME` syntax.
- **`~/.synapse/config.toml`** — structured config (server profiles, auth configs, preferences). **Auto-generated on first run** with commented examples showing each connection type. No deployment burden on user.

```toml
# Auto-generated by Synapse on first run
# Uncomment and modify to add server profiles

# [servers.my-local-server]
# transport = "stdio"
# command = "npx"
# args = ["@modelcontextprotocol/server-github"]
# auth = "pat"
# token_env = "GITHUB_TOKEN"        # name of env var from .env

# [servers.my-remote-server]
# transport = "streamable_http"
# url = "https://mcp.example.com"
# auth = "api_key"
# key_env = "MCP_API_KEY"           # name of env var from .env

# [servers.corp-gateway]
# transport = "streamable_http"
# url = "https://mcp-gateway.corp.com"
# auth = "oauth2"                   # triggers browser-based SSO flow

```

Proxy is a **CLI argument** (ephemeral, per-invocation), not config:
```
./synapse --proxy http://127.0.0.1:8080 --no-verify-ssl
```

If `~/.synapse/config.toml` doesn't exist on startup, the app auto-generates the commented template and continues (no server profiles defined = no auto-connections, user connects manually via REPL). This means zero setup friction — just run `./synapse` and go.

`~/.synapse/history` for command history persistence.

---

## Module System

Metasploit-inspired module architecture:

```python
class BaseModule(ABC):
    metadata: ClassVar[ModuleMetadata]   # name, description, author, category
    options: ClassVar[list[ModuleOption]] # configurable options (like MSF's RHOSTS, etc.)

    def __init__(self, session_manager: SessionManager): ...
    def set_option(self, name: str, value: Any) -> None: ...
    async def run(self) -> ModuleResult: ...
    async def check(self) -> bool: ...  # precondition validation
```

**Categories**: ENUMERATE, AUDIT, INVOKE, RECON

**Discovery**: Built-in modules found by walking `app.modules.*` subpackages. External modules register via `pyproject.toml` entry points under `synapse.modules`.

**Search**: The `search` command performs case-insensitive substring matching against module names and descriptions.

**MVP modules**:
- `enumerate/tools` — list tools across sessions
- `enumerate/resources` — list resources
- `enumerate/prompts` — list prompts
- `invoke/tool_call` — invoke a tool with user-provided JSON args (JSON because MCP is JSON-RPC; tool schemas are server-defined and vary)

---

## CLI / UX Design

### Context Stack (Stack-Based, Arbitrary Depth)

The REPL uses a **stack-based state machine** rather than a simple two-state toggle. MVP uses 2 levels but the stack supports arbitrary depth for future nested navigation (server browsing, tool inspection, etc.):

```
GLOBAL -> MODULE -> (future: SERVER_BROWSE -> TOOL_INSPECT -> ...)
  ^        |                                      |
  +--back--+                                      |
  ^                                               |
  +--------------------back-----------------------+
```

Each stack frame defines its available commands. `back` pops the stack. This scales to any depth without rewriting dispatch logic.

### Prompt Design

```
synapse >                                    # global, no session
synapse [mcp-github] >                      # global, active session
synapse (enumerate/tools) >                  # in module, no session
synapse (enumerate/tools) [mcp-github] >     # in module, active session
```

### Command Table

| Command | Context | Description |
|---------|---------|-------------|
| `help [cmd]` | Global | Show help |
| `connect <name> [transport] [opts]` | Global | Connect by profile name or ad-hoc |
| `disconnect <name>` | Global | Close connection |
| `sessions` | Global | List active connections |
| `sessions -i <id>` | Global | Switch active session |
| `use <module>` | Global | Load module into context |
| `search <query>` | Global | Search modules |
| `back` | Module | Return to global context |
| `show options` | Module | Display module options |
| `show info` | Module | Display module metadata |
| `set <opt> <val>` | Module | Set option |
| `unset <opt>` | Module | Clear option |
| `run` | Module | Execute module |
| `check` | Module | Validate preconditions |
| `tools [session]` | Any | List tools |
| `resources [session]` | Any | List resources |
| `prompts [session]` | Any | List prompts |
| `call <tool> [json]` | Any | Invoke a tool directly |
| `read <uri>` | Any | Read a resource |
| `exit` / `quit` | Global | Exit |

### Connect Command Examples

Profile-based (loads from `~/.synapse/config.toml`):
```
synapse > connect github                  # matches [servers.github] in config
synapse > connect corp                    # matches [servers.corp] — triggers OAuth2/SSO flow
```

Ad-hoc (inline args, no config entry needed):
```
synapse > connect github stdio --command npx --args @modelcontextprotocol/server-github --auth pat --token env:GITHUB_TOKEN
synapse > connect remote http --url https://mcp.example.com --auth api-key --key sk-abc123
synapse > connect corp http --url https://mcp-gateway.corp.com --auth oauth2
synapse > connect local stdio --command python --args -m my_mcp_server
```

When only a name is provided, `connect` looks up `[servers.<name>]` in the TOML config. If no profile matches and no transport is given, it fails with a helpful message listing available profiles.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp>=1.26,<2` | Official MCP Python SDK (ClientSession, transports, JSON-RPC) |
| `prompt_toolkit>=3.0` | REPL: async input, tab completion, history, key bindings |
| `rich>=13.0` | Terminal formatting: tables, panels, syntax highlighting |
| `python-dotenv` | .env file loading for secrets |
| `httpx` | Already dep of `mcp` — used for auth-configured HTTP clients |
| `pydantic>=2.0` | Already dep of `mcp` — config models, validation |
| `anyio>=4.0` | Already dep of `mcp` — async runtime (not raw asyncio) |

**Outer CLI**: `argparse` (stdlib) — no Click dependency.

**Dev**: `pytest`, `pytest-asyncio`, `ruff`, `mypy`
**Build tool**: `uv` (manages venv, dependencies, lockfile)

---

## MVP Scope (Weekend Build)

**In scope**:
- Project scaffolding: `./synapse` entry point, `app/` package, pyproject.toml, uv setup, README with setup instructions
- Core: TransportConfig/Factory (STDIO + HTTP), ConnectionManager, SessionManager
- Auth: ApiKeyAuth, PatAuth, OAuth2Auth (for corporate SSO — browser-based flow via MCP SDK's OAuthClientProvider)
- Config: TOML auto-generated to `~/.synapse/` + .env for secrets
- Events: basic event bus
- Models: separated into domain modules under `core/models/`
- Modules: BaseModule + registry + 4 built-in modules (enumerate/tools, resources, prompts + invoke/tool_call)
- CLI: full REPL with prompt_toolkit, stack-based context, all commands from table, rich formatted output, tab completion, ASCII banner embedded in banner.py
- End-to-end: launch synapse, connect to a real MCP server, enumerate tools, invoke a tool

**Deferred but architecturally supported**:
- AWS SSO, mTLS, OIDC, Kerberos auth (plugin slots ready)
- SSE transport (legacy)
- Audit modules (prompt injection testing, permission auditing, schema validation)
- Recon modules (server fingerprinting, transport detection)
- Export/reporting
- AI/LLM integration for red teaming workflows
- Session recording/replay
- Web UI (core is UI-independent, `app/main.py` routes to interface)
- Remote module loading
- Credential vault (encrypted token storage)
- `.rc` file scripted execution
- Advanced menu system (stack supports arbitrary depth)

---

## Implementation Sequence

### Day 1: Foundation + Core

1. **Scaffolding**: pyproject.toml, `./synapse` entry point (overwrite existing), `app/` package tree, README with uv + venv setup instructions
2. **Core models**: `app/core/models/*.py` (Pydantic models, one per domain), `app/core/errors.py`
3. **Config**: `app/core/config.py` (TOML + .env loading, auto-generate `~/.synapse/config.toml` on first run)
4. **Auth**: `app/core/auth/base.py` (AuthProvider protocol), `api_key.py`, `pat.py`, `oauth2.py`, `registry.py`
5. **Transport**: `app/core/transport.py` (TransportConfig, TransportType, factory)
6. **Connection**: `app/core/connection.py` (ManagedConnection, ConnectionManager)
7. **Session**: `app/core/session.py` (SessionManager)
8. **Events**: `app/core/events.py` (basic event bus)
9. **Integration test**: manually connect to a real stdio MCP server, list tools

### Day 2: Modules + CLI

1. **Module framework**: `app/modules/base.py`, `app/modules/registry.py`
2. **Built-in modules**: enumerate/tools, resources, prompts + invoke/tool_call
3. **CLI foundation**: banner.py (embedded ASCII art), context.py (stack-based), formatter.py
4. **Commands**: base.py (strategy pattern), registry.py, global_cmds.py, module_cmds.py, session_cmds.py
5. **REPL**: completer.py, repl.py
6. **App entry**: `app/main.py` (Synapse class)
7. **End-to-end test**: full workflow through the REPL

### Collaboration Model

- I build the boilerplate/scaffolding code; user reviews and tests
- When we reach MCP-specific implementation (transport wiring, session management, protocol operations), user is hands-on to learn the protocol
- OAuth2 auth provider prioritized for MVP — handles corporate SSO needed for testing week of 2026-03-30

---

## Verification

1. `./synapse` displays ASCII banner and drops into REPL
2. `connect test stdio --command npx --args @modelcontextprotocol/server-everything` establishes connection
3. `sessions` shows the active connection with tool/resource counts
4. `tools` lists discovered tools in a formatted table
5. `use enumerate/tools` -> `show options` -> `run` executes the module
6. `call echo '{"message": "hello"}'` invokes a tool directly and displays the result
7. `disconnect test` -> `exit` cleanly shuts down
8. `ruff check app/` passes with no errors
9. `mypy app/` passes with no errors
