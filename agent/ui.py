from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel


console = Console()


class Activity:

    def __init__(self):
        self.entries = []
        self.current = None
        self.live = None

    def start(self, message):
        self.current = (
            message,
            time.perf_counter(),
        )
        self.refresh()

    def finish(self, status, message):
        elapsed = self.elapsed()

        self.entries.append(
            (
                status,
                message,
                elapsed,
            )
        )

        self.current = None
        self.refresh()

    def success(self, message):
        self.finish("success", message)

    def warning(self, message):
        self.finish("warning", message)

    def error(self, message):
        self.finish("error", message)

    def elapsed(self):
        if not self.current:
            return 0.0

        return (
            time.perf_counter()
            - self.current[1]
        )

    def render(self):
        lines = []

        for (
            status,
            message,
            elapsed,
        ) in self.entries:

            icon = {
                "success": "[green]✓[/green]",
                "warning": "[yellow]•[/yellow]",
                "error": "[red]✗[/red]",
            }[status]

            lines.append(
                f"  {icon} "
                f"{message} "
                f"[dim]{elapsed:.2f}s[/dim]"
            )

        if self.current:

            lines.append(
                f"  [cyan]⠋[/cyan] "
                f"{self.current[0]} "
                f"[dim]{self.elapsed():.1f}s[/dim]"
            )

        return "\n".join(lines)

    def refresh(self):
        if self.live:
            self.live.update(
                self.render()
            )


def header(repo, config):

    console.print(
        Panel(
            f"[bold]Local Code Agent[/bold]\n"
            f"[dim]{repo.name}[/dim] · "
            f"[cyan]{config.model}[/cyan]\n"
            f"[dim]{config.ollama_url}[/dim]",
            border_style="blue",
            padding=(1, 2),
        )
    )


def result(text):

    console.print(
        Panel(
            Markdown(text),
            title="Result",
            border_style="green",
            padding=(1, 2),
        )
    )


def live_activity():

    return Live(
        "",
        console=console,
        refresh_per_second=12,
        transient=False,
    )