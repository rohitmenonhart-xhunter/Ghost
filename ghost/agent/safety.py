"""Safety Rails — Protect users from destructive actions.

Ghost must confirm before:
- Sending emails/messages
- Making purchases
- Deleting files/data
- Submitting forms with financial info
- Closing unsaved work

Kill switch: Cmd+Shift+Escape (or configurable) stops Ghost immediately.
"""

import platform
import threading
from typing import Callable, Optional

SYSTEM = platform.system()

# Actions that require user confirmation
DESTRUCTIVE_KEYWORDS = [
    "delete", "remove", "erase", "drop", "destroy", "uninstall",
    "send", "submit", "post", "publish", "share",
    "purchase", "buy", "pay", "checkout", "order", "subscribe",
    "sign out", "log out", "deactivate", "close account",
    "format", "reset", "factory reset", "wipe",
    "transfer", "wire", "withdraw",
]

SAFE_ACTIONS = [
    "click", "type", "scroll", "navigate", "open", "switch",
    "read", "search", "copy", "select",
]


class SafetyGuard:
    """Checks actions before execution and requests confirmation when needed."""

    def __init__(
        self,
        confirm_fn: Optional[Callable[[str], bool]] = None,
        auto_approve_safe: bool = True,
    ):
        # confirm_fn: called when confirmation needed. Returns True to proceed.
        # If None, uses terminal input.
        self._confirm_fn = confirm_fn or self._terminal_confirm
        self.auto_approve_safe = auto_approve_safe
        self._killed = False
        self._kill_event = threading.Event()

    def check_action(self, action: str, target: str = "", text: str = "") -> bool:
        """Check if an action is safe to execute.

        Returns True if safe or user confirmed. False to block.
        """
        if self._killed:
            return False

        full_context = f"{action} {target} {text}".lower()

        # Always allow safe actions
        if self.auto_approve_safe:
            action_lower = action.lower()
            if any(safe in action_lower for safe in SAFE_ACTIONS):
                if not any(danger in full_context for danger in DESTRUCTIVE_KEYWORDS):
                    return True

        # Check for destructive keywords
        is_destructive = any(kw in full_context for kw in DESTRUCTIVE_KEYWORDS)

        if is_destructive:
            return self._confirm_fn(
                f"Ghost wants to: {action}"
                + (f" on '{target}'" if target else "")
                + (f" with '{text}'" if text else "")
                + "\n  This looks like a potentially destructive action."
                + "\n  Allow? (y/n): "
            )

        return True

    def check_url(self, url: str) -> bool:
        """Check if a URL is safe to navigate to."""
        dangerous_patterns = [
            "payment", "checkout", "billing", "purchase",
            "delete-account", "deactivate",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in dangerous_patterns):
            return self._confirm_fn(
                f"Ghost wants to navigate to: {url}\n"
                f"  This URL looks sensitive. Allow? (y/n): "
            )
        return True

    def check_text_input(self, text: str) -> bool:
        """Check if text being typed contains sensitive info."""
        # Don't type things that look like passwords, credit cards, SSNs
        sensitive_patterns = [
            # Credit card-like (16 digits)
            r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
            # SSN-like
            r"\d{3}-\d{2}-\d{4}",
        ]
        import re
        for pattern in sensitive_patterns:
            if re.search(pattern, text):
                return self._confirm_fn(
                    f"Ghost wants to type text that looks like sensitive data.\n"
                    f"  Allow? (y/n): "
                )
        return True

    # ── Kill Switch ──────────────────────────────────────────────

    def kill(self):
        """Emergency stop. Blocks all future actions."""
        self._killed = True
        self._kill_event.set()
        print("\n  [KILLED] Ghost stopped by kill switch.")

    def resume(self):
        """Resume after kill switch."""
        self._killed = False
        self._kill_event.clear()

    @property
    def is_killed(self) -> bool:
        return self._killed

    def start_kill_listener(self):
        """Start listening for kill switch hotkey in background."""
        try:
            import pynput
            from pynput import keyboard

            kill_combo = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.Key.esc}
            current_keys = set()

            def on_press(key):
                current_keys.add(key)
                if kill_combo.issubset(current_keys):
                    self.kill()

            def on_release(key):
                current_keys.discard(key)

            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.daemon = True
            listener.start()
        except ImportError:
            pass  # pynput not installed, skip hotkey listener

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _terminal_confirm(message: str) -> bool:
        """Ask for confirmation via terminal input."""
        try:
            response = input(f"\n  [SAFETY] {message}")
            return response.strip().lower() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False
