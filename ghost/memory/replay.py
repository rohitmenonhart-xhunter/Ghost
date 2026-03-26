"""Task Replay Library — Learn once, replay forever.

Every task Ghost completes gets stored as a replayable action sequence.
Next time a similar task comes in → replay from library, zero AI calls.
For partially matching tasks → use as a hint for the AI ("expect this flow").

The library is per-user and grows dynamically.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher


class TaskReplayLibrary:
    """Persistent library of learned task sequences."""

    def __init__(self, library_dir: str = "./ghost_workspace/replay_library"):
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.library_dir / "index.json"
        self._index = self._load_index()

    def _load_index(self) -> list[dict]:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return []

    def _save_index(self):
        self.index_file.write_text(json.dumps(self._index, indent=2))

    # ── Store ────────────────────────────────────────────────────

    def store(self, task: str, actions: list[dict], success: bool, duration: float = 0):
        """Store a completed task's action sequence for future replay.

        actions: list of {"action": "CLICK_DOM", "target": "Log In", "element_id": 5, ...}
        """
        if not success or not actions:
            return

        # Normalize task description for matching
        task_key = self._normalize(task)

        entry = {
            "task": task,
            "task_key": task_key,
            "actions": actions,
            "success": success,
            "duration": duration,
            "replay_count": 0,
            "last_replayed": None,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Save action sequence
        filename = f"task_{len(self._index):04d}.json"
        (self.library_dir / filename).write_text(json.dumps(entry, indent=2))

        # Update index
        self._index.append({
            "task": task,
            "task_key": task_key,
            "filename": filename,
            "action_count": len(actions),
            "success": success,
        })
        self._save_index()

    # ── Lookup ───────────────────────────────────────────────────

    def find_exact(self, task: str) -> Optional[dict]:
        """Find an exact match for a task."""
        task_key = self._normalize(task)
        for entry in reversed(self._index):  # most recent first
            if entry["task_key"] == task_key and entry["success"]:
                return self._load_entry(entry["filename"])
        return None

    def find_similar(self, task: str, threshold: float = 0.6) -> list[dict]:
        """Find similar tasks that might inform the AI's approach.

        Returns matches with similarity score, sorted best-first.
        """
        task_key = self._normalize(task)
        matches = []

        for entry in self._index:
            if not entry["success"]:
                continue
            score = SequenceMatcher(None, task_key, entry["task_key"]).ratio()
            if score >= threshold:
                full = self._load_entry(entry["filename"])
                if full:
                    matches.append({**full, "similarity": score})

        return sorted(matches, key=lambda m: m["similarity"], reverse=True)

    def get_replay(self, task: str) -> Optional[list[dict]]:
        """Get a replayable action sequence for a task.

        Returns the action list if exact match found, None otherwise.
        """
        match = self.find_exact(task)
        if match:
            return match["actions"]
        return None

    def get_hint(self, task: str) -> Optional[str]:
        """Get a hint for the AI based on similar past tasks.

        Returns a text description of what to expect, for the AI's context.
        """
        similar = self.find_similar(task, threshold=0.5)
        if not similar:
            return None

        best = similar[0]
        actions_desc = []
        for i, a in enumerate(best["actions"], 1):
            desc = f"{i}. {a.get('action', '?')}"
            if a.get("target"):
                desc += f" '{a['target']}'"
            if a.get("url"):
                desc += f" → {a['url']}"
            actions_desc.append(desc)

        return (
            f"Similar task found ({best['similarity']:.0%} match): \"{best['task']}\"\n"
            f"That task used these steps:\n" + "\n".join(actions_desc) +
            f"\n\nUse this as a guide but verify each step — the page may have changed."
        )

    def mark_replayed(self, task: str):
        """Track that a task was successfully replayed."""
        task_key = self._normalize(task)
        for entry in self._index:
            if entry["task_key"] == task_key:
                full = self._load_entry(entry["filename"])
                if full:
                    full["replay_count"] = full.get("replay_count", 0) + 1
                    full["last_replayed"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    (self.library_dir / entry["filename"]).write_text(
                        json.dumps(full, indent=2)
                    )
                break

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Library statistics."""
        total = len(self._index)
        successful = sum(1 for e in self._index if e["success"])
        return {
            "total_tasks": total,
            "successful": successful,
            "total_actions": sum(e["action_count"] for e in self._index),
        }

    # ── Internal ─────────────────────────────────────────────────

    def _load_entry(self, filename: str) -> Optional[dict]:
        path = self.library_dir / filename
        if path.exists():
            return json.loads(path.read_text())
        return None

    @staticmethod
    def _normalize(task: str) -> str:
        """Normalize task for matching — lowercase, strip extras."""
        task = task.lower().strip()
        task = re.sub(r"[^\w\s@.]", "", task)  # keep alphanumeric, @, .
        task = re.sub(r"\s+", " ", task)
        return task
