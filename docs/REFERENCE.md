# MCP Protocol Reference

Quick reference for the Model Context Protocol as it relates to Synapse development.

## Overview

The Model Context Protocol (MCP) is an open standard developed by Anthropic (released November 2024) that enables integration between applications and external data sources/tools. It uses **JSON-RPC 2.0** for communication between three roles:

- **Host** — the application that initiates connections (Synapse)
- **Client** — a connector within the host that maintains a 1:1 session with a server
- **Server** — a service that exposes tools, resources, and prompts

Source: https://modelcontextprotocol.io/docs/learn/architecture

## Transport Types

| Transport | Use Case | Mechanism |
|-----------|----------|-----------|
| **STDIO** | Local servers | Client spawns server as child process, communicates via stdin/stdout |
| **Streamable HTTP** | Remote servers | HTTP POST/GET with optional SSE for streaming |
| **SSE** | Remote (legacy) | Deprecated — separate HTTP POST + SSE stream endpoints |

- STDIO is recommended for local integrations
- Streamable HTTP is recommended for remote/scalable deployments
- SSE is maintained for backward compatibility only

Source: https://modelcontextprotocol.io/docs/learn/transports

## Protocol Operations

### Discovery

| Method | Description |
|--------|-------------|
| `tools/list` | List all tools exposed by the server |
| `resources/list` | List all resources provided by the server |
| `prompts/list` | List all prompt templates offered by the server |

### Execution

| Method | Description |
|--------|-------------|
| `tools/call` | Invoke a tool with provided arguments (JSON object) |
| `resources/read` | Retrieve content from a resource by URI |
| `prompts/get` | Retrieve a specific prompt template |

### Lifecycle

| Method | Description |
|--------|-------------|
| `initialize` | Client/server handshake — exchange capabilities |
| `notifications/initialized` | Client signals initialization complete |
| `ping` | Keepalive / health check |

Source: https://modelcontextprotocol.io/specification/2025-11-25

## Three Primitives

Servers expose capabilities through three primitive types:

| Primitive | Controlled By | Description | Example |
|-----------|--------------|-------------|---------|
| **Tools** | Model | Executable functions | API calls, file operations, database queries |
| **Resources** | Application | Contextual data | File contents, git history, database records |
| **Prompts** | User | Template interactions | Slash commands, workflow templates |

Source: https://modelcontextprotocol.io/docs/learn/core-architecture

## Client Capabilities

During initialization, clients declare support for:

| Capability | Description |
|------------|-------------|
| `roots` | Filesystem boundaries the server can operate within |
| `sampling` | Server-initiated LLM interactions |
| `elicitation` | Server-initiated requests for user information |

Source: https://modelcontextprotocol.io/specification/2025-11-25/client

## Authentication

### Local (STDIO)

- Credentials passed via environment variables to the spawned server process
- No protocol-level auth — relies on the process environment

### Remote (HTTP)

- **OAuth 2.1** is the standard auth mechanism for remote MCP servers
- Flow: Client hits server -> 401 + OAuth metadata -> browser-based auth -> token exchange
- Server exposes Protected Resource Metadata (PRM) describing auth requirements
- Access tokens passed as Bearer tokens in Authorization header

### OAuth 2.1 Flow (Relevant to Corporate SSO)

1. Client sends request to MCP server
2. Server responds with `401 Unauthorized` + `WWW-Authenticate` header containing `resource_metadata`
3. Client fetches authorization server metadata
4. Client opens browser for user authentication (e.g., corporate SSO/AD login)
5. User authenticates, authorization server redirects back with auth code
6. Client exchanges auth code for access + refresh tokens
7. Client uses access token for subsequent requests

Source: https://modelcontextprotocol.io/docs/tutorials/security/authorization

## Python SDK

- **Package**: `mcp` (PyPI)
- **Repository**: https://github.com/modelcontextprotocol/python-sdk
- **Documentation**: https://py.sdk.modelcontextprotocol.io
- **Status**: Tier 1 (full-featured, production-ready)

### Key Client Classes

| Class | Purpose |
|-------|---------|
| `ClientSession` | Manages a single client-server session over a transport |
| `StdioServerParameters` | Configuration for spawning STDIO server processes |
| `streamable_http_client` | Async context manager for Streamable HTTP transport |
| `stdio_client` | Async context manager for STDIO transport |
| `OAuthClientProvider` | Handles OAuth 2.1 authorization code flow |

### Client Usage Pattern

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="npx",
    args=["@modelcontextprotocol/server-example"],
    env={"API_KEY": "..."},
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("tool_name", arguments={"key": "value"})
```

Source: https://py.sdk.modelcontextprotocol.io

## Security Considerations

- Treat all tool invocations as arbitrary code execution (untrusted)
- Obtain explicit user consent before invoking tools
- Do not rely on tool descriptions from untrusted servers
- Users must approve any LLM sampling requests
- Implement data privacy controls for resource access

Source: https://modelcontextprotocol.io/specification/2025-11-25#security

## Specification Links

| Resource | URL |
|----------|-----|
| Full Specification (2025-11-25) | https://modelcontextprotocol.io/specification/2025-11-25 |
| Architecture Overview | https://modelcontextprotocol.io/docs/learn/architecture |
| Python SDK Docs | https://py.sdk.modelcontextprotocol.io |
| Python SDK Repository | https://github.com/modelcontextprotocol/python-sdk |
| Transport Types | https://modelcontextprotocol.io/docs/learn/transports |
| Authorization Guide | https://modelcontextprotocol.io/docs/tutorials/security/authorization |
| Client Development Guide | https://modelcontextprotocol.io/docs/learn/clients |
