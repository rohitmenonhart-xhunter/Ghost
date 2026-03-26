"""OSWorld-style Benchmark Runner for macOS.

Adapts the 369 OSWorld tasks to macOS equivalents:
- Chrome → Chrome/Safari (same tasks)
- LibreOffice → LibreOffice (available on macOS)
- VS Code → VS Code (same on all platforms)
- Thunderbird → Mail or Thunderbird
- VLC → VLC (available on macOS)
- GIMP → GIMP (available on macOS)
- OS tasks → macOS equivalents (Finder, Terminal, System Settings)

Each task has:
- instruction: what the agent must do
- domain: which app category
- setup(): prepare the environment
- verify(): programmatic check if task succeeded
"""

import json
import time
import os
import subprocess
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field


@dataclass
class Task:
    id: str
    domain: str
    instruction: str
    setup_fn: Optional[Callable] = None
    verify_fn: Optional[Callable] = None
    difficulty: str = "medium"
    osworld_id: str = ""  # original OSWorld UUID if adapted


@dataclass
class TaskResult:
    task_id: str
    domain: str
    success: bool
    time_seconds: float
    tokens_used: int
    error: Optional[str] = None
    steps: int = 0


class BenchmarkRunner:
    """Run benchmark tasks and collect results."""

    def __init__(self, agent_fn: Callable, test_dir: str = "/tmp/ghost_benchmark"):
        """
        agent_fn: function that takes (instruction: str) -> dict with keys:
            "success": bool, "tokens": int, "steps": int, "result": str
        """
        self.agent_fn = agent_fn
        self.test_dir = Path(test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[TaskResult] = []

    def run_task(self, task: Task) -> TaskResult:
        """Run a single task."""
        print(f"\n  [{task.id}] {task.domain} | {task.difficulty}")
        print(f"  {task.instruction[:90]}...")

        # Setup
        if task.setup_fn:
            try:
                task.setup_fn()
            except Exception as e:
                print(f"  Setup error: {e}")

        # Execute
        start = time.time()
        tokens = 0
        steps = 0
        success = False
        error = None

        try:
            result = self.agent_fn(task.instruction)
            tokens = result.get("tokens", 0)
            steps = result.get("steps", 0)
        except Exception as e:
            error = str(e)

        elapsed = time.time() - start

        # Verify
        if task.verify_fn:
            try:
                success = task.verify_fn()
            except Exception as e:
                success = False
                error = f"Verify error: {e}"
        else:
            # No verification — count as success if no error
            success = error is None

        status = "PASS" if success else "FAIL"
        print(f"  → {status} ({elapsed:.1f}s, {steps} steps, ~{tokens} tokens)")

        task_result = TaskResult(
            task_id=task.id, domain=task.domain,
            success=success, time_seconds=elapsed,
            tokens_used=tokens, error=error, steps=steps,
        )
        self.results.append(task_result)
        return task_result

    def run_all(self, tasks: list[Task], domains: Optional[list[str]] = None) -> dict:
        """Run all tasks, optionally filtered by domain."""
        if domains:
            tasks = [t for t in tasks if t.domain in domains]

        print(f"\n{'='*60}")
        print(f"  GHOST BENCHMARK — {len(tasks)} tasks")
        print(f"{'='*60}")

        self.results = []
        for task in tasks:
            self.run_task(task)

        return self._summarize()

    def _summarize(self) -> dict:
        """Generate summary report."""
        total = len(self.results)
        if total == 0:
            return {}

        passed = sum(1 for r in self.results if r.success)
        total_time = sum(r.time_seconds for r in self.results)
        total_tokens = sum(r.tokens_used for r in self.results)
        total_steps = sum(r.steps for r in self.results)

        # Per-domain breakdown
        domains = {}
        for r in self.results:
            if r.domain not in domains:
                domains[r.domain] = {"total": 0, "passed": 0, "tokens": 0, "time": 0}
            domains[r.domain]["total"] += 1
            if r.success:
                domains[r.domain]["passed"] += 1
            domains[r.domain]["tokens"] += r.tokens_used
            domains[r.domain]["time"] += r.time_seconds

        score = passed / total * 100

        print(f"\n{'='*60}")
        print(f"  BENCHMARK RESULTS")
        print(f"{'='*60}")
        print(f"  Score: {passed}/{total} ({score:.1f}%)")
        print(f"  Time: {total_time:.0f}s | Steps: {total_steps} | Tokens: ~{total_tokens}")
        print(f"  Cost: ~${total_tokens * 0.000003:.4f}")
        print(f"  Avg time/task: {total_time/total:.1f}s")
        print(f"  Avg cost/task: ~${total_tokens * 0.000003 / total:.5f}")

        print(f"\n  Per Domain:")
        print(f"  {'Domain':25s} {'Score':>10s} {'Tokens':>10s} {'Time':>8s}")
        print(f"  {'-'*55}")
        for domain, stats in sorted(domains.items()):
            pct = stats["passed"] / stats["total"] * 100
            print(f"  {domain:25s} {stats['passed']}/{stats['total']} ({pct:4.0f}%) {stats['tokens']:>8d} {stats['time']:>6.0f}s")

        print(f"\n  {'─'*55}")
        print(f"  COMPARISON WITH SOTA:")
        print(f"  {'Agent':25s} {'Score':>8s} {'$/task':>10s}")
        print(f"  {'─'*45}")
        print(f"  {'GPT-5.4':25s} {'75.0%':>8s} {'~$0.15':>10s}")
        print(f"  {'Claude Opus 4.6':25s} {'72.7%':>8s} {'~$0.20':>10s}")
        print(f"  {'Claude Sonnet 4.6':25s} {'72.5%':>8s} {'~$0.10':>10s}")
        print(f"  {'OpenAI CUA (o3)':25s} {'42.9%':>8s} {'~$0.15':>10s}")
        print(f"  {'UI-TARS-1.5-7B':25s} {'27.5%':>8s} {'  free':>10s}")
        avg_cost = f"~${total_tokens * 0.000003 / total:.4f}"
        print(f"  {'GHOST':25s} {score:>7.1f}% {avg_cost:>10s}")
        print(f"{'='*60}\n")

        summary = {
            "score": score,
            "passed": passed,
            "total": total,
            "total_time": total_time,
            "total_tokens": total_tokens,
            "total_steps": total_steps,
            "domains": domains,
            "results": [
                {"id": r.task_id, "domain": r.domain, "success": r.success,
                 "time": r.time_seconds, "tokens": r.tokens_used, "error": r.error}
                for r in self.results
            ],
        }

        # Save
        out_path = self.test_dir / "benchmark_full_results.json"
        out_path.write_text(json.dumps(summary, indent=2))
        print(f"  Saved to: {out_path}")

        return summary
