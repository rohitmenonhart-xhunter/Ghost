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
    console.print("  [dim]Commands: /help /loop /model /memory /tasks /quit[/dim]")
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
            help_table.add_row("  /loop [task]", "Repeat a task until Ctrl+C, then summarize")
            help_table.add_row("  /model [name]", "Switch LLM model")
            help_table.add_row("  /memory", "Show what Ghost remembers")
            help_table.add_row("  /tasks", "Show completed tasks")
            help_table.add_row("  /tabs", "List open browser tabs")
            help_table.add_row("  /screenshot", "Save current screen")
            help_table.add_row("  /clear", "Clear terminal")
            help_table.add_row("  /quit", "Exit Ghost")
            help_table.add_row("", "")
            help_table.add_row("  [anything else]", "Ghost executes it as a task")
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

        elif user_input.lower().startswith("/loop"):
            # ── Loop Mode ─────────────────────────────────────
            parts = user_input.split(None, 1)
            if len(parts) < 2:
                console.print("  [dim]Usage: /loop <task>[/dim]")
                console.print("  [dim]Example: /loop Search Upwork for Python jobs and apply to matching ones[/dim]")
                console.print("  [dim]Press Ctrl+C to stop the loop and get a summary.[/dim]")
                continue

            loop_task = parts[1].strip()
            _run_loop(console, agent, browser, apps, memory, api_key, current_model, loop_task)
            continue

        # ── Execute Single Task ───────────────────────────────
        task_count += 1
        result = _run_single_task(console, agent, browser, apps, memory, api_key, current_model, user_input, task_count)

    # Cleanup
    console.print()


def _run_single_task(console, agent, browser, apps, memory, api_key, model, user_input, task_num) -> Optional[str]:
    """Execute a single task and return a smart response."""
    from rich.panel import Panel

    console.print()
    console.print(f"  [bold bright_red]Task #{task_num}[/bold bright_red] [white]{user_input[:80]}[/white]")
    console.print()

    memory.log(f"Task: {user_input}")
    result_text = None

    try:
        apps.switch_to_app("Google Chrome", fullscreen=True)
        time.sleep(0.5)

        if not browser.is_available():
            from ghost.browser.cdp import BrowserController
            browser = BrowserController()
            browser.launch_with_debugging()
            time.sleep(3)

        # Determine task type
        browser_keywords = ["go to", "navigate", "browse", "website", "http", ".com",
                            ".org", ".io", "search", "google", "click", "sign in",
                            "log in", "upload", "download", "fill", "form", "apply",
                            "find", "get", "check", "open"]
        system_keywords = ["create file", "save to", "run command", "terminal",
                           "open app", "close app", "clipboard", "find file"]

        is_browser = any(kw in user_input.lower() for kw in browser_keywords)
        is_system = any(kw in user_input.lower() for kw in system_keywords)

        if is_browser or (not is_system):
            raw_result = agent.run(user_input, max_steps=20)

            # ── Smart Response: ask AI to summarize what happened ──
            import openai
            client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

            summary_prompt = f"""You are Ghost, a browser agent. You just completed a task.

Task the user asked for: {user_input}

Raw result from browser agent: {str(raw_result)[:1000]}

Give a clean, concise response to the user about what you did and what you found.
- If you extracted data, present it clearly
- If you completed an action, confirm what was done
- If something failed, explain what went wrong
- Be direct, no fluff
- Use bullet points for lists"""

            resp = client.chat.completions.create(
                model=model, max_tokens=500,
                messages=[{"role": "user", "content": summary_prompt}],
            )
            result_text = resp.choices[0].message.content.strip()

            console.print()
            console.print(Panel(
                result_text[:800],
                title="[bold green]✓ Done[/bold green]",
                border_style="green",
                padding=(1, 2),
            ))
            memory.log(f"Result: {result_text[:200]}")

        else:
            # System task
            import openai
            client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            resp = client.chat.completions.create(
                model=model, max_tokens=500,
                messages=[{"role": "user", "content": f"Complete this task using shell commands. Reply with ONLY the commands.\n\nTask: {user_input}"}],
            )
            commands = resp.choices[0].message.content.strip()

            import subprocess
            output_lines = []
            for line in commands.split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("```"):
                    continue
                console.print(f"  [dim]$ {line}[/dim]")
                try:
                    r = subprocess.run(line, shell=True, capture_output=True, text=True, timeout=15)
                    if r.stdout.strip():
                        console.print(f"  {r.stdout.strip()[:200]}")
                        output_lines.append(r.stdout.strip()[:200])
                except Exception as e:
                    console.print(f"  [red]Error: {e}[/red]")

            result_text = "\n".join(output_lines) if output_lines else "Done"
            console.print(f"  [green]✓ Done.[/green]")

    except KeyboardInterrupt:
        console.print("\n  [yellow]Task interrupted.[/yellow]")
    except Exception as e:
        console.print(f"  [red]Error: {e}[/red]")

    return result_text


def _run_loop(console, agent, browser, apps, memory, api_key, model, task):
    """Run a task in continuous loop until user presses Ctrl+C.

    Each iteration: execute → collect result → repeat
    On stop: summarize all iterations.
    """
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    console.print()
    console.print(Panel(
        f"[bold white]🔄 Loop Mode[/bold white]\n\n"
        f"[white]Task: {task}[/white]\n\n"
        f"[dim]Ghost will repeat this task continuously.\n"
        f"Press Ctrl+C to stop and get a summary.[/dim]",
        border_style="bright_red",
        padding=(1, 2),
    ))
    console.print()

    iteration = 0
    results = []
    start_time = time.time()

    try:
        while True:
            iteration += 1
            console.print(f"  [bold bright_red]── Iteration {iteration} ──[/bold bright_red]")

            # Build the iteration-specific prompt
            if iteration == 1:
                iter_task = task
            else:
                # Tell AI to continue where it left off, find new items
                prev_summary = "; ".join(r[:50] for r in results[-3:])
                iter_task = (
                    f"{task}\n\n"
                    f"This is iteration #{iteration}. Previous results: {prev_summary}\n"
                    f"Find NEW items, don't repeat what was already done."
                )

            try:
                apps.switch_to_app("Google Chrome", fullscreen=True)
                time.sleep(0.3)

                if not browser.is_available():
                    from ghost.browser.cdp import BrowserController
                    browser = BrowserController()
                    browser.launch_with_debugging()
                    time.sleep(3)

                raw_result = agent.run(iter_task, max_steps=20)

                # Summarize this iteration
                import openai
                client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
                resp = client.chat.completions.create(
                    model=model, max_tokens=300,
                    messages=[{"role": "user", "content": f"Briefly summarize what was accomplished in this iteration.\nTask: {task}\nResult: {str(raw_result)[:500]}\nOne paragraph, be specific."}],
                )
                iter_summary = resp.choices[0].message.content.strip()
                results.append(iter_summary)

                console.print(f"  [green]✓ {iter_summary[:120]}[/green]")
                console.print()

                memory.log(f"Loop iteration {iteration}: {iter_summary[:100]}")

            except Exception as e:
                console.print(f"  [red]Error in iteration {iteration}: {e}[/red]")
                results.append(f"Error: {e}")

            # Brief pause between iterations
            console.print(f"  [dim]Starting next iteration in 3s... (Ctrl+C to stop)[/dim]")
            time.sleep(3)

    except KeyboardInterrupt:
        pass

    # ── Loop Summary ──────────────────────────────────────────
    elapsed = time.time() - start_time

    console.print()
    console.print()

    # Generate final summary
    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

        all_results = "\n".join(f"Iteration {i+1}: {r}" for i, r in enumerate(results))
        resp = client.chat.completions.create(
            model=model, max_tokens=800,
            messages=[{"role": "user", "content": f"""Summarize all the work done in this loop session.

Task: {task}
Total iterations: {iteration}
Total time: {elapsed:.0f} seconds

Results per iteration:
{all_results}

Give a clean final summary with:
- What was accomplished overall
- Key items/data collected
- Total count of actions taken
- Any issues encountered
Use bullet points. Be specific."""}],
        )
        final_summary = resp.choices[0].message.content.strip()
    except Exception:
        final_summary = "\n".join(f"• Iteration {i+1}: {r[:100]}" for i, r in enumerate(results))

    # Display summary
    summary_table = Table(box=box.SIMPLE, padding=(0, 2), show_header=False)
    summary_table.add_column("", style="dim")
    summary_table.add_column("")
    summary_table.add_row("Iterations", f"[white]{iteration}[/white]")
    summary_table.add_row("Time", f"[white]{elapsed:.0f}s[/white]")
    summary_table.add_row("Results", f"[white]{len([r for r in results if not r.startswith('Error')])} successful[/white]")

    console.print(Panel(
        f"{final_summary}\n\n",
        title=f"[bold bright_red]🔄 Loop Summary — {iteration} iterations[/bold bright_red]",
        border_style="bright_red",
        padding=(1, 2),
    ))
    console.print(summary_table)
    console.print()

    # Save summary to file
    summary_path = os.path.expanduser(f"~/ghost_loop_summary_{time.strftime('%Y%m%d_%H%M%S')}.md")
    with open(summary_path, "w") as f:
        f.write(f"# Ghost Loop Summary\n\n")
        f.write(f"**Task:** {task}\n")
        f.write(f"**Iterations:** {iteration}\n")
        f.write(f"**Time:** {elapsed:.0f}s\n\n")
        f.write(f"## Summary\n\n{final_summary}\n\n")
        f.write(f"## Iteration Details\n\n")
        for i, r in enumerate(results):
            f.write(f"### Iteration {i+1}\n{r}\n\n")

    console.print(f"  [dim]Summary saved to {summary_path}[/dim]")
    memory.log(f"Loop completed: {iteration} iterations for '{task[:50]}'")
    memory.remember(f"Loop task '{task[:40]}' ran {iteration} iterations")


def cli_entry():
    """Entry point for `ghost` command."""
    main()


if __name__ == "__main__":
    main()
