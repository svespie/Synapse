"""Synapse application entry point."""

from __future__ import annotations

import sys

from rich.console import Console

from app.cli.banner import display_banner


class Synapse:
    """Main application class. Boots core services and launches the interface."""

    def __init__(
        self,
        *,
        verbose: bool = False,
        show_banner: bool = True,
        proxy_url: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self.verbose = verbose
        self.show_banner = show_banner
        self.proxy_url = proxy_url
        self.verify_ssl = verify_ssl
        self.console = Console()

    def run(self) -> None:
        """Launch the application."""
        if self.show_banner:
            display_banner(self.console)

        # TODO: Boot core services and launch REPL
        sys.exit(0)
