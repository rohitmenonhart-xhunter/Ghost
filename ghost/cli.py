"""Ghost CLI — Terminal agent that controls your computer.

Run it. Talk to it. It does things on your real system.

$ ghost
╭──────────────────────────────────────╮
│  👻 Ghost v0.2.0                     │
│  Your AI browser agent.              │
│  Type a task. Ghost does it.         │
╰──────────────────────────────────────╯

> Sign into Upwork and apply to matching jobs
  [Ghost opens Chrome, navigates, fills forms...]
  ✓ Done.

> /quit
"""

import os
import sys
import time
import signal
from typing import Optional


def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80


def main():
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.markdown import Markdown
    from rich import box

    console = Console()

    # ── Header ───────────────────────────────────────────────
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold white]👻 Ghost[/bold white] [dim]v0.2.0[/dim]\n"
            "[white]AI browser agent. DOM + OCR + Memory.[/white]\n"
            "[dim]Type a task. Ghost does it on your real system.[/dim]"
        ),
        border_style="bright_red",
        box=box.DOUBLE_EDGE,
        padding=(1, 3),
    ))

    # ── Permission Check ─────────────────────────────────────
    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not api_key:
        console.print()
        console.print("[bold red]  No API key found.[/bold red]")
        console.print("  Set your OpenRouter key:")
        console.print("  [dim]export OPENROUTER_API_KEY=\"your-key-here\"[/dim]")
        console.print("  Get one free at [link=https://openrouter.ai]openrouter.ai[/link]")
        console.print()
        return

    # ── Permissions ───────────────────────────────────────────
    console.print()
    console.print("[bold bright_red]  Permissions[/bold bright_red]")
    console.print()

    permissions = {
        "Browser Control": "Open, navigate, click, type in Chrome via DevTools",
        "Screen Reading": "Capture screenshots, read text via OCR",
        "File System": "Read/write files, manage downloads",
        "Clipboard": "Read/write system clipboard",
        "App Management": "Open, close, switch applications",
        "Keyboard/Mouse": "Click, type, scroll, hotkeys on your system",
    }

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Permission", style="white")
    table.add_column("Description", style="dim")

    for perm, desc in permissions.items():
        table.add_row(f"  ◉ {perm}", desc)

    console.print(table)
    console.print()

    try:
        grant = Prompt.ask(
            "  [bold]Grant all permissions?[/bold] Ghost needs these to control your computer",
            choices=["y", "n"],
            default="y",
        )
    except (EOFError, KeyboardInterrupt):
        console.print("\n  [dim]Bye.[/dim]")
        return

    if grant.lower() != "y":
        console.print("  [dim]Ghost needs permissions to work. Exiting.[/dim]")
        return

    console.print("  [green]✓ All permissions granted.[/green]")
    console.print()

    # ── Initialize ────────────────────────────────────────────
    with console.status("[bold bright_red]  Starting Ghost...[/bold bright_red]", spinner="dots"):
        from ghost.browser.cdp import BrowserController
        from ghost.browser.agent import BrowserAgent
        from ghost.agent.apps import AppController
        from ghost.agent.filesystem import FileSystem
        from ghost.agent.clipboard import Clipboard
        from ghost.memory.memory import GhostMemory

        browser = BrowserController()
        if not browser.is_available():
            browser.launch_with_debugging()
            time.sleep(3)

        apps = AppController()
        fs = FileSystem()
        clipboard = Clipboard()
        memory = GhostMemory()

        agent = BrowserAgent(
            provider="openrouter",
            model="anthropic/claude-sonnet-4",
            api_key=api_key,
        )

    console.print("  [green]✓ Ghost is ready.[/green]")
    console.print()
    console.print("  [dim]Commands: /help /model /memory /tasks /quit[/dim]")
    console.print()

    # ── Model state ───────────────────────────────────────────
    current_model = "anthropic/claude-sonnet-4"
    task_count = 0

    # ── REPL Loop ─────────────────────────────────────────────
    while True:
        try:
            console.print()
            user_input = Prompt.ask("[bold bright_red]  ghost[/bold bright_red]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n  [dim]👻 Ghost vanishes...[/dim]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # ── Commands ──────────────────────────────────────────

        if user_input.lower() in ("/quit", "/exit", "/q"):
            console.print("  [dim]👻 Ghost vanishes...[/dim]")
            break

        elif user_input.lower() == "/help":
            console.print()
            help_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
            help_table.add_column("Command", style="bold white")
            help_table.add_column("Description", style="dim")
            help_table.add_row("  /help", "Show this help")
            help_table.add_row("  /model [name]", "Switch LLM model")
            help_table.add_row("  /memory", "Show what Ghost remembers")
            help_table.add_row("  /tasks", "Show completed tasks")
            help_table.add_row("  /tabs", "List open browser tabs")
            help_table.add_row("  /screenshot", "Save current screen")
            help_table.add_row("  /clear", "Clear terminal")
            help_table.add_row("  /quit", "Exit Ghost")
            help_table.add_row("", "")
            help_table.add_row("  [anything else]", "Ghost executes it as a browser task")
            console.print(help_table)
            continue

        elif user_input.lower().startswith("/model"):
            parts = user_input.split(None, 1)
            if len(parts) > 1:
                current_model = parts[1].strip()
                agent = BrowserAgent(
                    provider="openrouter",
                    model=current_model,
                    api_key=api_key,
                )
                console.print(f"  [green]✓ Switched to {current_model}[/green]")
            else:
                console.print(f"  [white]Current model: {current_model}[/white]")
                console.print("  [dim]Usage: /model anthropic/claude-sonnet-4-6[/dim]")
            continue

        elif user_input.lower() == "/memory":
            mem_content = memory.read_memory()
            if mem_content.strip():
                console.print()
                console.print(Panel(mem_content[:1000], title="[bold]MEMORY.md[/bold]", border_style="bright_red"))
            else:
                console.print("  [dim]No memories yet. Ghost learns as you use it.[/dim]")
            continue

        elif user_input.lower() == "/tasks":
            tasks = memory.list_tasks()
            if tasks:
                t = Table(box=box.SIMPLE, padding=(0, 1))
                t.add_column("ID", style="dim")
                t.add_column("Task", style="white")
                t.add_column("Status", style="green")
                for task in tasks[-10:]:
                    status_color = "green" if task["status"] == "completed" else "yellow"
                    t.add_row(task["id"], task["title"][:60], f"[{status_color}]{task['status']}[/{status_color}]")
                console.print(t)
            else:
                console.print("  [dim]No tasks yet.[/dim]")
            continue

        elif user_input.lower() == "/tabs":
            try:
                from ghost.browser.tabs import TabManager
                tm = TabManager(browser)
                console.print(tm.format_for_llm())
            except Exception:
                console.print("  [dim]Could not read tabs.[/dim]")
            continue

        elif user_input.lower() == "/screenshot":
            from ghost.agent.screen import ScreenCapture
            sc = ScreenCapture()
            path = "/tmp/ghost_screenshot.png"
            sc.capture().save(path)
            console.print(f"  [green]✓ Saved to {path}[/green]")
            continue

        elif user_input.lower() == "/clear":
            console.clear()
            continue

        # ── Execute Task ──────────────────────────────────────
        task_count += 1
        console.print()
        console.print(f"  [bold bright_red]Task #{task_count}[/bold bright_red] [white]{user_input[:80]}[/white]")
        console.print()

        # Log to memory
        memory.log(f"Task: {user_input}")

        try:
            # Ensure browser is ready
            apps.switch_to_app("Google Chrome", fullscreen=True)
            time.sleep(0.5)

            if not browser.is_available():
                browser.launch_with_debugging()
                time.sleep(3)

            # Determine if this is a browser task or system task
            browser_keywords = ["go to", "navigate", "browse", "website", "http", ".com",
                                ".org", ".io", "search", "google", "click", "sign in",
                                "log in", "upload", "download", "fill", "form"]
            system_keywords = ["create file", "save to", "run command", "terminal",
                               "open app", "close app", "clipboard", "find file"]

            is_browser = any(kw in user_input.lower() for kw in browser_keywords)
            is_system = any(kw in user_input.lower() for kw in system_keywords)

            if is_browser or (not is_system):
                # Browser task
                result = agent.run(user_input, max_steps=20)
                if result:
                    console.print()
                    console.print(Panel(
                        str(result)[:500],
                        title="[bold green]✓ Result[/bold green]",
                        border_style="green",
                    ))
                    memory.log(f"Result: {str(result)[:200]}")
                else:
                    console.print("  [yellow]Task completed (no output).[/yellow]")

            else:
                # System task — use AI + terminal
                import openai
                client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
                resp = client.chat.completions.create(
                    model=current_model, max_tokens=500,
                    messages=[{"role": "user", "content": f"Complete this task using macOS shell commands. Reply with ONLY the commands, one per line.\n\nTask: {user_input}"}],
                )
                commands = resp.choices[0].message.content.strip()

                import subprocess
                for line in commands.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("```"):
                        continue
                    console.print(f"  [dim]$ {line}[/dim]")
                    try:
                        r = subprocess.run(line, shell=True, capture_output=True, text=True, timeout=15)
                        if r.stdout.strip():
                            console.print(f"  {r.stdout.strip()[:200]}")
                    except Exception as e:
                        console.print(f"  [red]Error: {e}[/red]")

                console.print("  [green]✓ Done.[/green]")

        except KeyboardInterrupt:
            console.print("\n  [yellow]Task interrupted.[/yellow]")
        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")

    # Cleanup
    console.print()


def cli_entry():
    """Entry point for `ghost` command."""
    main()


if __name__ == "__main__":
    main()
