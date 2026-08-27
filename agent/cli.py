from __future__ import annotations

import argparse
import sys
import shutil

import requests

from . import __version__
from .agent import Agent
from .config import Config
from .repository import git_root
from .ui import (
    Activity,
    console,
    header,
    live_activity,
    result,
)


def doctor():

    config = Config.load()

    repo = git_root()


    console.print()

    console.print(
        "[bold]Local Code Agent Doctor[/bold]"
    )

    console.print("─" * 40)

    console.print()


    # Python

    console.print(
        f"  [green]✓[/green] "
        f"Python {sys.version.split()[0]}"
    )


    # Git

    if shutil.which("git"):

        console.print(
            "  [green]✓[/green] Git"
        )

    else:

        console.print(
            "  [red]✗[/red] "
            "Git not found"
        )


    # ripgrep

    if shutil.which("rg"):

        console.print(
            "  [green]✓[/green] "
            "ripgrep"
        )

    else:

        console.print(
            "  [red]✗[/red] "
            "ripgrep not found"
        )


    console.print()

    console.print(
        "[bold]Ollama[/bold]"
    )

    console.print(
        f"  URL: {config.ollama_url}"
    )


    try:

        response = requests.get(

            (
                f"{config.ollama_url}"
                "/api/tags"
            ),

            timeout=5,
        )

        response.raise_for_status()

        console.print(
            "  [green]✓[/green] "
            "Server reachable"
        )


        models = {

            model.get("name")

            for model in response.json().get(
                "models",
                [],
            )
        }


        if config.model in models:

            console.print(
                f"  [green]✓[/green] "
                f"Model {config.model}"
            )

        else:

            console.print(
                f"  [yellow]![/yellow] "
                f"Model {config.model} "
                f"was not found"
            )


    except Exception as exc:

        console.print(
            f"  [red]✗[/red] "
            f"Server unreachable: {exc}"
        )


    console.print()

    console.print(
        "[bold]Repository[/bold]"
    )


    if repo:

        console.print(
            f"  [green]✓[/green] "
            f"{repo}"
        )

    else:

        console.print(
            "  [yellow]![/yellow] "
            "No Git repository detected"
        )


    console.print()


def config_command():

    config = Config.load()


    console.print()

    console.print(
        "[bold]Local Code Agent Configuration[/bold]"
    )

    console.print("─" * 40)

    console.print()


    try:

        url = input(
            f"Ollama URL "
            f"[{config.ollama_url}]: "
        ).strip()


        model = input(
            f"Model "
            f"[{config.model}]: "
        ).strip()


    except (
        EOFError,
        KeyboardInterrupt,
    ):

        console.print(
            "\nCancelled."
        )

        return


    if url:

        config.ollama_url = url


    if model:

        config.model = model


    path = config.save()


    console.print()

    console.print(
        f"[green]✓[/green] "
        f"Saved to {path}"
    )

    console.print()


def run_agent(question):

    repo = git_root()


    if repo is None:

        console.print(
            "[red]No Git repository "
            "found.[/red]"
        )

        console.print(
            "Run lca from inside "
            "a Git repository."
        )

        return 1


    config = Config.load()

    activity = Activity()


    header(
        repo,
        config,
    )


    console.print(
        f"[bold]>[/bold] "
        f"{question}"
    )

    console.print()


    with live_activity() as live:

        activity.live = live


        agent = Agent(
            repo,
            config,
            activity,
        )


        try:

            answer = agent.run(
                question
            )


        except requests.RequestException as exc:

            activity.error(
                "Could not reach Ollama"
            )

            activity.live = None

            live.update("")


            console.print(
                f"\n[red]Ollama request failed:[/red]\n"
                f"{exc}\n"
            )

            console.print(
                "Run [bold]lca doctor[/bold]"
                " for diagnostics."
            )

            return 1


        except Exception as exc:

            activity.error(
                "Agent failed"
            )

            activity.live = None

            live.update("")


            console.print(
                f"\n[red]Error:[/red] {exc}"
            )

            return 1


        activity.live = None

        live.update("")


    console.print()

    result(answer)

    return 0


def interactive():

    repo = git_root()


    if repo is None:

        console.print(
            "[red]No Git repository "
            "found.[/red]"
        )

        return 1


    config = Config.load()


    header(
        repo,
        config,
    )


    console.print(
        "[dim]Type 'exit' or 'quit' "
        "to leave.[/dim]"
    )

    console.print()


    while True:

        try:

            question = console.input(
                "[bold cyan]"
                "local-agent>"
                "[/bold cyan] "
            ).strip()


        except (
            EOFError,
            KeyboardInterrupt,
        ):

            console.print()

            return 0


        if not question:

            continue


        if question.lower() in (
            "exit",
            "quit",
        ):

            return 0


        run_agent(question)

        console.print()


def main():

    parser = argparse.ArgumentParser(
        prog="lca",
        description=(
            "Local Code Agent"
        ),
    )


    parser.add_argument(
        "question",
        nargs="*",
    )


    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"%(prog)s "
            f"{__version__}"
        ),
    )


    args = parser.parse_args()


    # Commands first.

    if len(sys.argv) >= 2:

        command = sys.argv[1]


        if command == "doctor":

            doctor()

            return 0


        if command == "config":

            config_command()

            return 0


        if command == "version":

            print(__version__)

            return 0


    # One-shot.

    if args.question:

        return run_agent(
            " ".join(args.question)
        )


    # Interactive.

    return interactive()


if __name__ == "__main__":

    raise SystemExit(
        main()
    )