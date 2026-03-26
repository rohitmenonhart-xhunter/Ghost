"""Ghost Memory System — Active, agent-managed, file-based persistence.

Ghost doesn't just log — it THINKS about what to remember.
After each task, the VLM reflects: what worked, what failed, what to remember.
The VLM reads and writes memory files directly.

Inspired by OpenClaw: "if it's not written to a file, it doesn't exist."
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class GhostMemory:
    """Active file-based memory. Ghost reads and writes these files itself."""

    def __init__(self, workspace: str = "./ghost_workspace"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "memory").mkdir(exist_ok=True)
        (self.workspace / "tasks").mkdir(exist_ok=True)

        self._ensure_core_files()

    # ── Bootstrap ────────────────────────────────────────────────

    def _ensure_core_files(self):
        """Create core files with defaults if missing."""
        for name, default in [
            ("SOUL.md", DEFAULT_SOUL),
            ("MEMORY.md", DEFAULT_MEMORY),
            ("USER.md", DEFAULT_USER),
        ]:
            path = self.workspace / name
            if not path.exists():
                path.write_text(default)

    # ── Read Operations (Ghost reads before acting) ──────────────

    def read(self, filename: str) -> str:
        """Read any file in the workspace. Returns '' if missing."""
        path = self.workspace / filename
        if path.exists() and path.is_file():
            return path.read_text()
        return ""

    def read_soul(self) -> str:
        return self.read("SOUL.md")

    def read_memory(self) -> str:
        return self.read("MEMORY.md")

    def read_user(self) -> str:
        return self.read("USER.md")

    def read_today_log(self) -> str:
        return self.read(f"memory/{datetime.now().strftime('%Y-%m-%d')}.md")

    def read_yesterday_log(self) -> str:
        d = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return self.read(f"memory/{d}.md")

    def read_task(self, task_id: str) -> str:
        return self.read(f"tasks/{task_id}/task.md")

    # ── Write Operations (Ghost writes during & after tasks) ─────

    def write(self, filename: str, content: str):
        """Write/overwrite a file in the workspace."""
        path = self.workspace / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def append(self, filename: str, content: str):
        """Append a line to a file. Creates if missing."""
        path = self.workspace / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(content if content.endswith("\n") else content + "\n")

    def edit_section(self, filename: str, section: str, new_content: str):
        """Replace content under a ## section heading.

        Finds '## <section>' and replaces everything until the next '##' or EOF.
        """
        path = self.workspace / filename
        if not path.exists():
            return

        text = path.read_text()
        header = f"## {section}"

        if header not in text:
            # Section doesn't exist — append it
            text += f"\n\n{header}\n{new_content}\n"
            path.write_text(text)
            return

        # Find section boundaries
        start = text.index(header)
        after_header = start + len(header)

        # Find next ## or EOF
        rest = text[after_header:]
        next_section = re.search(r"\n## ", rest)
        if next_section:
            end = after_header + next_section.start()
        else:
            end = len(text)

        # Replace
        text = text[:after_header] + "\n" + new_content + "\n" + text[end:]
        path.write_text(text)

    # ── Episodic Log (timestamped daily entries) ─────────────────

    def log(self, entry: str):
        """Append a timestamped entry to today's log."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = f"memory/{date_str}.md"

        if not self.read(log_file):
            self.write(log_file, f"# Ghost Log — {date_str}\n\n")

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append(log_file, f"- [{timestamp}] {entry}")

    # ── Memory (cross-session knowledge, kept lean) ──────────────

    def remember(self, entry: str):
        """Add an entry to MEMORY.md. Ghost calls this for important learnings."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.append("MEMORY.md", f"- [{timestamp}] {entry}")
        self._trim_memory()

    def forget(self, pattern: str):
        """Remove lines matching pattern from MEMORY.md."""
        content = self.read_memory()
        lines = content.split("\n")
        filtered = [l for l in lines if pattern.lower() not in l.lower()]
        self.write("MEMORY.md", "\n".join(filtered))

    def _trim_memory(self):
        """Keep MEMORY.md under 100 lines. Oldest entries get pruned."""
        content = self.read_memory()
        lines = content.split("\n")
        if len(lines) <= 100:
            return

        # Keep headers (lines starting with #) + most recent entries
        headers = [l for l in lines if l.startswith("#") or l.startswith("_")]
        entries = [l for l in lines if l.startswith("- [")]
        other = [l for l in lines if l and not l.startswith("#")
                 and not l.startswith("_") and not l.startswith("- [")]

        # Keep all headers + last N entries to fit 100 lines
        max_entries = 100 - len(headers) - len(other) - 5  # buffer
        trimmed = headers + other + entries[-max_entries:]
        self.write("MEMORY.md", "\n".join(trimmed) + "\n")

    # ── Task Files ───────────────────────────────────────────────

    def create_task(self, task_id: str, description: str) -> str:
        """Create a task.md file. Returns the file path."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""# Task: {description}

## Meta
- **ID:** {task_id}
- **Created:** {timestamp}
- **Status:** in_progress

## Plan
_To be determined._

## Actions
_Step-by-step log of what Ghost did._

## Observations
_What Ghost noticed, errors encountered, UI state changes._

## Learnings
_What Ghost learned from this task that applies to future tasks._

## Result
_Pending._
"""
        filepath = f"tasks/{task_id}/task.md"
        self.write(filepath, content)
        return filepath

    def update_task_status(self, task_id: str, status: str):
        """Update task status: in_progress, completed, failed."""
        filepath = f"tasks/{task_id}/task.md"
        content = self.read(filepath)
        if not content:
            return
        content = re.sub(
            r"\*\*Status:\*\* \w+",
            f"**Status:** {status}",
            content,
        )
        self.write(filepath, content)

    def task_log(self, task_id: str, section: str, entry: str):
        """Append a timestamped entry to a task section."""
        filepath = f"tasks/{task_id}/task.md"
        content = self.read(filepath)
        if not content:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        header = f"## {section}"

        if header not in content:
            content += f"\n{header}\n- [{timestamp}] {entry}\n"
        else:
            # Insert after the header's existing content
            parts = content.split(header)
            before = parts[0]
            after = parts[1]

            # Find the next section or EOF
            next_match = re.search(r"\n## ", after)
            if next_match:
                insert_at = next_match.start()
                after = after[:insert_at] + f"\n- [{timestamp}] {entry}" + after[insert_at:]
            else:
                after = after.rstrip() + f"\n- [{timestamp}] {entry}\n"

            content = before + header + after

        self.write(filepath, content)

    def list_tasks(self, status: Optional[str] = None) -> list[dict]:
        """List all tasks."""
        tasks_dir = self.workspace / "tasks"
        results = []
        if not tasks_dir.exists():
            return results

        for task_dir in sorted(tasks_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            content = self.read(f"tasks/{task_dir.name}/task.md")
            if not content:
                continue

            # Extract status
            s_match = re.search(r"\*\*Status:\*\* (\w+)", content)
            task_status = s_match.group(1) if s_match else "unknown"

            if status and task_status != status:
                continue

            title = content.split("\n")[0].replace("# Task: ", "")
            results.append({"id": task_dir.name, "title": title, "status": task_status})

        return results

    # ── Search (find relevant past experience) ───────────────────

    def search(self, query: str, days: int = 14) -> list[dict]:
        """Search recent logs + memory for relevant entries."""
        results = []
        query_lower = query.lower()

        # Search MEMORY.md
        for line in self.read_memory().split("\n"):
            if query_lower in line.lower() and line.strip():
                results.append({"source": "MEMORY.md", "content": line.strip()})

        # Search recent daily logs
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            content = self.read(f"memory/{date_str}.md")
            for line in content.split("\n"):
                if query_lower in line.lower() and line.strip():
                    results.append({"source": f"memory/{date_str}.md", "content": line.strip()})

        # Search task files
        tasks_dir = self.workspace / "tasks"
        if tasks_dir.exists():
            for task_dir in tasks_dir.iterdir():
                content = self.read(f"tasks/{task_dir.name}/task.md")
                for line in content.split("\n"):
                    if query_lower in line.lower() and line.strip():
                        results.append({
                            "source": f"tasks/{task_dir.name}/task.md",
                            "content": line.strip(),
                        })

        return results[:20]  # cap results

    # ── Reflection (VLM-driven, called after tasks) ──────────────

    def build_reflection_prompt(self, task_id: str) -> str:
        """Build a prompt for the VLM to reflect on a completed task.

        The VLM reads the task file and decides:
        - What to add to MEMORY.md (reusable knowledge)
        - What to update in USER.md (user preferences learned)
        - What to log to today's episodic memory
        """
        task_content = self.read_task(task_id)
        memory_content = self.read_memory()

        return f"""You just completed a task. Review what happened and decide what to remember.

## Task File
{task_content}

## Current MEMORY.md
{memory_content}

Instructions:
1. If you learned something reusable (a pattern, a UI location, a trick), write it as a REMEMBER line.
2. If you learned something about the user, write it as a USER line.
3. If you noticed an error pattern to avoid, write it as a RULE line.
4. If nothing is worth remembering, write NOTHING.

Reply in this format (one per line, skip categories with nothing to add):
REMEMBER: <reusable knowledge for future tasks>
RULE: <mistake to avoid in the future>
USER: <something learned about the user>
LOG: <brief summary of what happened>
NOTHING
"""

    def apply_reflection(self, vlm_response: str):
        """Parse the VLM's reflection and write to appropriate files."""
        for line in vlm_response.strip().split("\n"):
            line = line.strip()
            if not line or line == "NOTHING":
                continue

            if line.startswith("REMEMBER:"):
                entry = line[len("REMEMBER:"):].strip()
                self.remember(entry)

            elif line.startswith("RULE:"):
                entry = line[len("RULE:"):].strip()
                self.remember(f"[RULE] {entry}")

            elif line.startswith("USER:"):
                entry = line[len("USER:"):].strip()
                # Append to USER.md
                current = self.read_user()
                if entry not in current:
                    self.append("USER.md", f"- {entry}")

            elif line.startswith("LOG:"):
                entry = line[len("LOG:"):].strip()
                self.log(entry)

    # ── System Prompt Assembly ────────────────────────────────────

    def build_system_prompt(self, task: Optional[str] = None) -> str:
        """Assemble full system prompt from all memory files.

        This is what the VLM sees at the start of every interaction.
        """
        parts = []

        # Identity
        soul = self.read_soul()
        if soul.strip():
            parts.append(soul)

        # User profile
        user = self.read_user()
        if user.strip() and user != DEFAULT_USER:
            parts.append(f"## About the User\n{user}")

        # Cross-session memory
        memory = self.read_memory()
        if memory.strip() and memory != DEFAULT_MEMORY:
            parts.append(f"## What You Remember\n{memory}")

        # Today's context
        today = self.read_today_log()
        if today.strip():
            parts.append(f"## Today's Activity\n{today}")

        # Yesterday's context (for continuity)
        yesterday = self.read_yesterday_log()
        if yesterday.strip():
            parts.append(f"## Yesterday\n{yesterday}")

        # Active tasks
        active = self.list_tasks(status="in_progress")
        if active:
            task_lines = "\n".join(f"- [{t['id']}] {t['title']}" for t in active)
            parts.append(f"## Active Tasks\n{task_lines}")

        # Current task
        if task:
            parts.append(f"## Current Task\n{task}")

        return "\n\n---\n\n".join(parts)

    # ── Convenience ──────────────────────────────────────────────

    def describe_tools(self) -> str:
        """Return a description of memory tools for the VLM's system prompt."""
        return """## Memory Tools Available
You can manage your memory during tasks. Use these in your responses when needed:

- REMEMBER: <fact> → Save to long-term memory (MEMORY.md)
- FORGET: <pattern> → Remove matching entries from memory
- LOG: <entry> → Add to today's daily log
- NOTE: <observation> → Add to current task's observations
- LEARN: <lesson> → Add to current task's learnings (promoted to memory on reflection)
- USER: <preference> → Update user profile

Write these as standalone lines in your response. Ghost will parse and execute them.
"""


# ── Default Templates ────────────────────────────────────────────

DEFAULT_SOUL = """# Ghost — Autonomous Digital Worker

## Core Identity
You are Ghost, an autonomous computer control agent. You see the screen,
move the mouse, type on the keyboard, and complete tasks — just like a human
sitting at the computer.

## Principles
1. **Act, don't talk.** Execute actions on a real computer. Don't just describe what you'd do.
2. **Observe first.** Study the screenshot carefully before every action. Read text, identify elements, understand state.
3. **One step at a time.** Do one action, verify it worked, then decide the next.
4. **Recover from errors.** If something fails, try differently. Never repeat a failed action unchanged.
5. **Remember everything.** Write observations and learnings to memory files. If it's not written down, it didn't happen.
6. **Ask when truly stuck.** After 3 failed attempts at the same thing, stop and note what went wrong.

## How You See
- You receive screenshots with a labeled grid overlay
- Grid cells are labeled (A1, B2, C3, etc.) at the top-left corner of each cell
- To click something, identify its grid cell — Ghost will zoom in for precision
- After each action, you get a fresh screenshot to verify the result

## Action Format
For each step, respond with:
REASONING: <what you see and why you're choosing this action>
ACTION: <CLICK, TYPE, HOTKEY, SCROLL, or DONE>
TARGET: <for CLICK: describe the exact UI element>
TEXT: <for TYPE: text to enter. for HOTKEY: key combo. for DONE: summary>

## Memory Protocol
- Before starting: check memory for relevant past experience
- When you learn something: write REMEMBER: <fact> in your response
- When corrected: write REMEMBER: [RULE] <what to do differently>
- When you notice a user preference: write USER: <preference>
- Keep observations flowing — they become training data

## Boundaries
- Never type passwords unless explicitly provided by the user
- Confirm before destructive actions (delete, close unsaved, send messages)
- If you see a CAPTCHA, stop and note it
- Don't make purchases or send communications without explicit approval
"""

DEFAULT_MEMORY = """# Ghost Memory

## Learned Rules
_Ghost adds rules here when it learns from mistakes._

## Known Patterns
_Reusable knowledge about UI locations, workflows, shortcuts._

## Environment
_System info, installed apps, display details._
"""

DEFAULT_USER = """# User Profile

_Ghost learns about you as you work together._
"""
