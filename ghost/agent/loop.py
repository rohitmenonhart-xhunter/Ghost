"""Ghost Agent Loop — Observe → Think → Grid → Locate → Act → Remember.

The agent actively manages its own memory:
- Reads MEMORY.md before starting for past learnings
- Parses inline memory commands from VLM responses (REMEMBER:, LOG:, etc.)
- Runs a reflection step after task completion
- The VLM decides what's worth remembering, not hardcoded logic
"""

import re
import time
import hashlib
from dataclasses import dataclass, field
from typing import Callable, Optional

from PIL import Image

from ghost.agent.screen import ScreenCapture
from ghost.agent.input_control import InputController
from ghost.agent.apps import AppController
from ghost.vision.vlm import GhostEyes
from ghost.memory.memory import GhostMemory


@dataclass
class ActionResult:
    step: int
    action: str
    target: Optional[str]
    coordinates: Optional[tuple[int, int]]
    text: Optional[str]
    reasoning: str
    screenshot: Optional[Image.Image] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentState:
    task: str
    task_id: str
    steps: list[ActionResult] = field(default_factory=list)
    is_done: bool = False
    result: Optional[str] = None
    current_step: int = 0


class GhostAgent:
    """Autonomous computer control agent with persistent memory.

    Pipeline per step:
    1. OBSERVE  — capture screenshot
    2. THINK    — VLM sees gridded screenshot + memory context, decides action
    3. LOCATE   — recursive grid zoom to find exact click coordinates
    4. ACT      — execute mouse/keyboard action
    5. REMEMBER — log action + outcome to task file and episodic memory
    """

    def __init__(
        self,
        eyes: GhostEyes,
        screen: Optional[ScreenCapture] = None,
        controller: Optional[InputController] = None,
        apps: Optional[AppController] = None,
        memory: Optional[GhostMemory] = None,
        max_steps: int = 30,
        on_action: Optional[Callable[[ActionResult], None]] = None,
    ):
        self.eyes = eyes
        self.screen = screen or ScreenCapture()
        self.controller = controller or InputController(scale_factor=1.0)
        self.apps = apps or AppController()
        self.memory = memory or GhostMemory()
        self.max_steps = max_steps
        self.on_action = on_action

    def run(self, task: str) -> AgentState:
        """Execute a task autonomously."""
        # Create task tracking
        task_id = hashlib.md5(f"{task}{time.time()}".encode()).hexdigest()[:8]
        self.memory.create_task(task_id, task)
        self.memory.log(f"Starting task: {task}")

        # Check past experience
        past = self.memory.search(task.split()[0], days=7)
        if past:
            self.memory.task_log(task_id, "Observations", f"Found {len(past)} related past entries")

        state = AgentState(task=task, task_id=task_id)
        start = time.time()

        # Build system prompt with full memory context
        system_prompt = self.memory.build_system_prompt(task=task)

        print(f"\n{'='*60}")
        print(f"  GHOST — {task}")
        print(f"  Task ID: {task_id}")
        print(f"{'='*60}\n")

        while not state.is_done and state.current_step < self.max_steps:
            result = self._step(state, system_prompt)
            state.steps.append(result)
            state.current_step += 1

            # Log to task file
            action_desc = f"{result.action}"
            if result.target:
                action_desc += f" '{result.target}'"
            if result.coordinates:
                action_desc += f" at ({result.coordinates[0]},{result.coordinates[1]})"
            status = "OK" if result.success else f"FAILED: {result.error}"
            self.memory.task_log(task_id, "Actions", f"{action_desc} → {status}")

            # Parse inline memory commands from VLM reasoning
            self._parse_memory_commands(result.reasoning, task_id)

            if self.on_action:
                self.on_action(result)

            if result.action == "DONE":
                state.is_done = True
                state.result = result.text
                break

            if not result.success:
                print(f"  [!] Step {result.step} failed: {result.error}")
                self.memory.task_log(task_id, "Observations", f"Step {result.step} failed: {result.error}")

            time.sleep(1)

        elapsed = time.time() - start

        # Record outcome
        if state.is_done:
            self.memory.update_task_status(task_id, "completed")
            self.memory.task_log(task_id, "Result", state.result or "Completed")
            self.memory.log(f"Task completed: {task} → {state.result}")
        else:
            self.memory.update_task_status(task_id, "incomplete")
            self.memory.task_log(task_id, "Result", f"Incomplete after {state.current_step} steps")
            self.memory.log(f"Task incomplete: {task} ({state.current_step} steps)")

        # Reflection: ask VLM what to remember from this task
        self._reflect(task_id)

        status_str = "DONE" if state.is_done else "INCOMPLETE"
        print(f"\n{'='*60}")
        print(f"  {status_str} in {elapsed:.0f}s ({state.current_step} steps)")
        if state.result:
            print(f"  Result: {state.result}")
        print(f"{'='*60}\n")

        return state

    def _step(self, state: AgentState, system_prompt: str) -> ActionResult:
        """One observe → think → locate → act cycle."""
        step_num = state.current_step + 1
        screenshot = self.screen.capture()

        # Build history
        history_parts = []
        for s in state.steps[-5:]:
            entry = s.action
            if s.target:
                entry += f" '{s.target}'"
            if s.text and s.action in ("TYPE", "HOTKEY"):
                entry += f" '{s.text}'"
            entry += " → OK" if s.success else f" → FAILED: {s.error}"
            history_parts.append(entry)
        history = " | ".join(history_parts)

        # 1. THINK
        print(f"  Step {step_num}: Thinking...", end=" ", flush=True)
        decision = self.eyes.decide_action(screenshot, state.task, history)

        action = decision["action"]
        target = decision.get("target")
        text = decision.get("text")
        reasoning = decision.get("reasoning", "")

        print(f"→ {action}", end="")
        if target:
            print(f" '{target}'", end="")
        if text and action in ("TYPE", "HOTKEY"):
            print(f" '{text}'", end="")
        print()
        if reasoning:
            short = reasoning[:120] + "..." if len(reasoning) > 120 else reasoning
            print(f"    {short}")

        result = ActionResult(
            step=step_num, action=action, target=target,
            coordinates=None, text=text, reasoning=reasoning,
            screenshot=screenshot,
        )

        if action == "DONE":
            return result

        # Programmatic actions — no grounding or verification needed
        programmatic = ("OPEN_APP", "OPEN_URL", "CLOSE_APP", "SWITCH_APP")
        if action in programmatic:
            try:
                self._execute(action, None, text)
                time.sleep(1)
            except Exception as e:
                result.success = False
                result.error = str(e)
            return result

        # 2. LOCATE — grid zoom for click actions
        if action in ("CLICK", "DOUBLE_CLICK", "RIGHT_CLICK") and target:
            print(f"  Locating '{target}'...")
            coords = self.eyes.locate(screenshot, target, verbose=True)
            result.coordinates = coords

            if coords is None:
                result.success = False
                result.error = f"Could not find: '{target}'"
                return result

        # 3. ACT
        try:
            self._execute(action, result.coordinates, text)
        except Exception as e:
            result.success = False
            result.error = str(e)
            return result

        # 4. VERIFY — for clicks, check the action worked
        if action in ("CLICK", "DOUBLE_CLICK", "RIGHT_CLICK"):
            time.sleep(1.5)
            verify_screenshot = self.screen.capture()
            verified = self._verify_action(verify_screenshot, action, target, state.task)
            if not verified:
                result.success = False
                result.error = f"Verification failed: action may not have worked as expected"
                print(f"    [VERIFY] Action may not have had the expected effect")

        return result

    def _execute(self, action: str, coords: Optional[tuple[int, int]], text: Optional[str]):
        """Execute an action via input controller or app controller."""
        if action == "CLICK" and coords:
            self.controller.click(coords[0], coords[1])
        elif action == "DOUBLE_CLICK" and coords:
            self.controller.double_click(coords[0], coords[1])
        elif action == "RIGHT_CLICK" and coords:
            self.controller.right_click(coords[0], coords[1])
        elif action == "TYPE" and text:
            self.controller.type_text(text)
        elif action == "HOTKEY" and text:
            self.controller.hotkey(text)
        elif action == "SCROLL":
            direction = text.lower() if text and text.lower() in ("up", "down") else "down"
            amount = 5
            mx, my = self.controller.mouse_position
            self.controller.scroll(mx, my, direction, amount)
        elif action == "WAIT":
            time.sleep(2)

        # Programmatic app control — no clicking needed
        elif action == "OPEN_APP" and text:
            self.apps.open_app(text)
        elif action == "OPEN_URL" and text:
            # Parse "url [browser]" format
            parts = text.split(" in ")
            url = parts[0].strip()
            browser = parts[1].strip() if len(parts) > 1 else None
            self.apps.open_url(url, browser)
        elif action == "CLOSE_APP" and text:
            self.apps.close_app(text)
        elif action == "SWITCH_APP" and text:
            self.apps.switch_to_app(text)

        elif action == "DONE":
            pass
        else:
            raise ValueError(f"Unknown action: {action}")

    def _verify_action(
        self, screenshot: Image.Image, action: str, target: str, task: str
    ) -> bool:
        """Verify an action worked by asking the VLM to check the new screenshot."""
        prompt = (
            f"I just performed this action: {action} on '{target}'\n"
            f"Overall task: {task}\n\n"
            f"Look at this screenshot taken AFTER the action. "
            f"Did the action have the expected effect? "
            f"For example, if I clicked an app icon, did that app open? "
            f"If I clicked a button, did the expected result appear?\n\n"
            f"Reply with ONLY 'YES' or 'NO' followed by a brief reason."
        )

        try:
            response = self.eyes.vlm.ask(screenshot, prompt, max_tokens=64)
            response = response.strip().upper()
            passed = response.startswith("YES")
            if not passed:
                print(f"    [VERIFY] VLM says: {response[:80]}")
            return passed
        except Exception:
            # If verification fails, assume action was OK (don't block on verification errors)
            return True

    def _parse_memory_commands(self, text: str, task_id: str):
        """Parse inline memory commands from VLM output.

        The VLM can write these in its reasoning to manage memory:
          REMEMBER: <fact>      → saved to MEMORY.md
          RULE: <lesson>        → saved to MEMORY.md as [RULE]
          LOG: <entry>          → saved to today's episodic log
          NOTE: <observation>   → saved to task observations
          LEARN: <lesson>       → saved to task learnings
          USER: <preference>    → saved to USER.md
          FORGET: <pattern>     → removes matching entries from MEMORY.md
        """
        if not text:
            return

        for line in text.split("\n"):
            line = line.strip()

            if line.startswith("REMEMBER:"):
                entry = line[len("REMEMBER:"):].strip()
                if entry:
                    self.memory.remember(entry)
                    print(f"    [MEM] Remembered: {entry[:60]}")

            elif line.startswith("RULE:"):
                entry = line[len("RULE:"):].strip()
                if entry:
                    self.memory.remember(f"[RULE] {entry}")
                    print(f"    [MEM] Rule added: {entry[:60]}")

            elif line.startswith("LOG:"):
                entry = line[len("LOG:"):].strip()
                if entry:
                    self.memory.log(entry)

            elif line.startswith("NOTE:"):
                entry = line[len("NOTE:"):].strip()
                if entry:
                    self.memory.task_log(task_id, "Observations", entry)

            elif line.startswith("LEARN:"):
                entry = line[len("LEARN:"):].strip()
                if entry:
                    self.memory.task_log(task_id, "Learnings", entry)

            elif line.startswith("USER:"):
                entry = line[len("USER:"):].strip()
                if entry:
                    current = self.memory.read_user()
                    if entry not in current:
                        self.memory.append("USER.md", f"- {entry}")
                        print(f"    [MEM] User noted: {entry[:60]}")

            elif line.startswith("FORGET:"):
                pattern = line[len("FORGET:"):].strip()
                if pattern:
                    self.memory.forget(pattern)
                    print(f"    [MEM] Forgot: {pattern[:60]}")

    def _reflect(self, task_id: str):
        """Post-task reflection: VLM reviews what happened and saves learnings."""
        print("  Reflecting on task...", end=" ", flush=True)
        try:
            prompt = self.memory.build_reflection_prompt(task_id)
            # Use a simple screenshot-free VLM call for reflection
            from ghost.vision.grid import GridOverlay
            # Create a minimal 1x1 image (API requires an image)
            dummy = Image.new("RGB", (100, 100), (0, 0, 0))
            response = self.eyes.vlm.ask(dummy, prompt)
            self.memory.apply_reflection(response)
            print("done.")
        except Exception as e:
            print(f"skipped ({e})")
