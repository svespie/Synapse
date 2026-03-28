# Synapse

MCP interaction framework for security professionals.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installing uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc   # or restart your shell
uv --version      # verify installation
```

## Setup

```bash
# Clone the repo
git clone https://github.com/svespie/Synapse.git
cd Synapse

# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"

# Activate the virtual environment
source .venv/bin/activate
```

### Secrets

Copy the sample env file and add your tokens/keys:

```bash
cp .env.sample .env
```

Edit `.env` with the credentials needed for your MCP server connections. This file is gitignored and never committed.

### Configuration

On first run, Synapse auto-generates `~/.synapse/config.toml` with commented examples for server profiles. No manual setup required.

## Usage

```bash
./synapse
```

### Options

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Enable verbose output |
| `--no-banner` | Skip the ASCII banner on startup |
| `--proxy URL` | HTTP proxy (e.g. `http://127.0.0.1:8080` for Burp Suite) |
| `--no-verify-ssl` | Disable SSL verification (for proxy TLS interception) |

## Project Structure

```
Synapse/
├── synapse              # Executable entry point
├── app/
│   ├── main.py          # Application class
│   ├── core/            # Core library (UI-independent)
│   │   ├── auth/        # Pluggable auth providers
│   │   ├── models/      # Pydantic data models
│   │   ├── connection.py, session.py, transport.py, config.py, events.py
│   ├── modules/         # Metasploit-style modules
│   │   ├── enumerate/   # Discovery modules
│   │   ├── invoke/      # Execution modules
│   │   ├── audit/       # Security audit modules
│   │   └── recon/       # Reconnaissance modules
│   └── cli/             # Terminal interface (prompt_toolkit + rich)
│       └── commands/    # Command implementations
├── tests/
└── docs/
    ├── DESIGN_MVP.md    # Architecture and design document
    └── REFERENCE.md     # MCP protocol reference
```

## Documentation

- [Design Document](docs/DESIGN_MVP.md) — architecture, component design, MVP scope
- [MCP Protocol Reference](docs/REFERENCE.md) — protocol operations, transports, auth, SDK usage

## License

MIT
