"""ASCII art banner and display logic."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from app import __version__

BANNER_ART: str = r"""
   ███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
   ██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
   ███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗
   ╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝
   ███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████╗
   ╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝
"""

TAGLINE: str = "MCP Interaction Framework for Security Professionals"


def display_banner(console: Console) -> None:
    """Render the startup banner with version and status info."""
    banner_text = Text(BANNER_ART, style="bold cyan")
    console.print(banner_text, highlight=False)

    console.print(f"        {TAGLINE}", style="dim white")
    console.print(f"        v{__version__}", style="dim white")
    console.print()
