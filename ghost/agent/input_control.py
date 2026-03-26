"""Bulletproof cross-platform mouse & keyboard control.

Handles: clicks (left/right/middle/double), typing (unicode-safe),
hotkeys (platform-aware), scrolling, dragging, and all edge cases.
"""

import platform
import time
import subprocess
from typing import Optional

import pyautogui

# Safety: move mouse to top-left corner to abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03  # tiny pause between pyautogui calls


SYSTEM = platform.system()  # "Darwin", "Linux", "Windows"

# macOS key name mapping — pyautogui uses different names
MAC_KEY_MAP = {
    "cmd": "command", "meta": "command", "super": "command", "win": "command",
    "ctrl": "command",  # on mac, most shortcuts use cmd not ctrl
    "control": "ctrl",  # explicit "control" means actual ctrl key
    "alt": "option", "opt": "option",
    "return": "enter", "esc": "escape",
    "del": "delete", "backspace": "backspace",
    "space": "space", "tab": "tab",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "pageup": "pageup", "pagedown": "pagedown",
    "home": "home", "end": "end",
}

LINUX_KEY_MAP = {
    "cmd": "ctrl", "command": "ctrl", "meta": "super", "win": "super",
    "option": "alt", "opt": "alt",
    "return": "enter", "esc": "escape",
    "del": "delete",
}


def _normalize_key(key: str) -> str:
    """Normalize key names for the current platform."""
    key = key.strip().lower()
    if SYSTEM == "Darwin":
        return MAC_KEY_MAP.get(key, key)
    elif SYSTEM == "Linux":
        return LINUX_KEY_MAP.get(key, key)
    return key


class InputController:
    """Reliable mouse and keyboard control."""

    def __init__(self, scale_factor: float = 1.0):
        self.scale_factor = scale_factor

        # Verify we have accessibility permissions on macOS
        if SYSTEM == "Darwin":
            self._check_macos_permissions()

    def _check_macos_permissions(self):
        """Warn if accessibility permissions aren't granted."""
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first process'],
                capture_output=True, timeout=5,
            )
            if result.returncode != 0:
                print(
                    "  [WARNING] Accessibility permission not granted.\n"
                    "  Go to: System Settings → Privacy & Security → Accessibility\n"
                    "  Add your terminal app (Terminal, iTerm, VS Code, etc.)"
                )
        except Exception:
            pass

    def _to_screen(self, x: int, y: int) -> tuple[int, int]:
        """Convert image coordinates to screen coordinates."""
        if self.scale_factor != 1.0:
            return int(x / self.scale_factor), int(y / self.scale_factor)
        return x, y

    # ── Mouse: Click ─────────────────────────────────────────────

    def click(self, x: int, y: int):
        """Left click at (x, y)."""
        sx, sy = self._to_screen(x, y)
        pyautogui.moveTo(sx, sy, duration=0.25)
        time.sleep(0.05)
        pyautogui.click(sx, sy)
        time.sleep(0.15)

    def double_click(self, x: int, y: int):
        """Double left click at (x, y)."""
        sx, sy = self._to_screen(x, y)
        pyautogui.moveTo(sx, sy, duration=0.25)
        time.sleep(0.05)
        pyautogui.doubleClick(sx, sy)
        time.sleep(0.15)

    def right_click(self, x: int, y: int):
        """Right click at (x, y)."""
        sx, sy = self._to_screen(x, y)
        pyautogui.moveTo(sx, sy, duration=0.25)
        time.sleep(0.05)
        pyautogui.rightClick(sx, sy)
        time.sleep(0.15)

    def middle_click(self, x: int, y: int):
        """Middle click at (x, y)."""
        sx, sy = self._to_screen(x, y)
        pyautogui.moveTo(sx, sy, duration=0.25)
        time.sleep(0.05)
        pyautogui.middleClick(sx, sy)
        time.sleep(0.15)

    def click_and_hold(self, x: int, y: int, duration: float = 1.0):
        """Click and hold at (x, y) for given duration."""
        sx, sy = self._to_screen(x, y)
        pyautogui.moveTo(sx, sy, duration=0.25)
        pyautogui.mouseDown(sx, sy)
        time.sleep(duration)
        pyautogui.mouseUp(sx, sy)

    # ── Mouse: Movement ──────────────────────────────────────────

    def move_to(self, x: int, y: int, duration: float = 0.25):
        """Move mouse to (x, y) without clicking."""
        sx, sy = self._to_screen(x, y)
        pyautogui.moveTo(sx, sy, duration=duration)

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        """Drag from (x1,y1) to (x2,y2)."""
        sx1, sy1 = self._to_screen(x1, y1)
        sx2, sy2 = self._to_screen(x2, y2)
        pyautogui.moveTo(sx1, sy1, duration=0.2)
        time.sleep(0.05)
        pyautogui.drag(sx2 - sx1, sy2 - sy1, duration=duration, button="left")
        time.sleep(0.15)

    # ── Mouse: Scroll ────────────────────────────────────────────

    def scroll(self, x: int, y: int, direction: str = "down", amount: int = 3):
        """Scroll at (x, y). Direction: 'up' or 'down'."""
        sx, sy = self._to_screen(x, y)
        pyautogui.moveTo(sx, sy, duration=0.15)
        clicks = amount if direction == "up" else -amount
        pyautogui.scroll(clicks, sx, sy)
        time.sleep(0.2)

    # ── Keyboard: Typing ─────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.02):
        """Type text safely. Handles unicode via clipboard on macOS."""
        if not text:
            return

        # Check if text is pure ASCII — pyautogui handles this fine
        if all(ord(c) < 128 for c in text):
            pyautogui.typewrite(text, interval=interval)
        else:
            # Unicode text: use clipboard paste method
            self._type_via_clipboard(text)

        time.sleep(0.1)

    def _type_via_clipboard(self, text: str):
        """Type text by copying to clipboard and pasting. Unicode-safe."""
        import subprocess

        if SYSTEM == "Darwin":
            # Copy to clipboard
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
            time.sleep(0.05)
            # Paste
            pyautogui.hotkey("command", "v")

        elif SYSTEM == "Linux":
            try:
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
                )
                process.communicate(text.encode("utf-8"))
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
            except FileNotFoundError:
                # Fallback: xdotool
                subprocess.run(["xdotool", "type", "--clearmodifiers", text])

        elif SYSTEM == "Windows":
            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-16-le"))
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")

        time.sleep(0.1)

    # ── Keyboard: Keys & Hotkeys ─────────────────────────────────

    def press_key(self, key: str):
        """Press a single key."""
        normalized = _normalize_key(key)
        pyautogui.press(normalized)
        time.sleep(0.1)

    def hotkey(self, *keys: str):
        """Press a key combination. Handles platform-specific mappings.

        Examples:
            hotkey("cmd", "c")       → Cmd+C on mac, Ctrl+C on linux
            hotkey("ctrl", "shift", "p") → proper combo on all platforms
            hotkey("alt", "tab")     → Option+Tab on mac, Alt+Tab on linux
            hotkey("enter")          → just press enter
        """
        if len(keys) == 1 and "+" in keys[0]:
            # Handle "cmd+c" format
            keys = tuple(keys[0].split("+"))

        normalized = [_normalize_key(k) for k in keys]

        # Filter empty strings
        normalized = [k for k in normalized if k]

        if not normalized:
            return

        if len(normalized) == 1:
            pyautogui.press(normalized[0])
        else:
            pyautogui.hotkey(*normalized)

        time.sleep(0.15)

    # ── Convenience ──────────────────────────────────────────────

    def enter(self):
        """Press Enter."""
        pyautogui.press("enter")
        time.sleep(0.1)

    def escape(self):
        """Press Escape."""
        pyautogui.press("escape")
        time.sleep(0.1)

    def tab(self):
        """Press Tab."""
        pyautogui.press("tab")
        time.sleep(0.1)

    def select_all(self):
        """Select all (Cmd+A / Ctrl+A)."""
        if SYSTEM == "Darwin":
            pyautogui.hotkey("command", "a")
        else:
            pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)

    def copy(self):
        """Copy selection (Cmd+C / Ctrl+C)."""
        if SYSTEM == "Darwin":
            pyautogui.hotkey("command", "c")
        else:
            pyautogui.hotkey("ctrl", "c")
        time.sleep(0.1)

    def paste(self):
        """Paste clipboard (Cmd+V / Ctrl+V)."""
        if SYSTEM == "Darwin":
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)

    def undo(self):
        """Undo (Cmd+Z / Ctrl+Z)."""
        if SYSTEM == "Darwin":
            pyautogui.hotkey("command", "z")
        else:
            pyautogui.hotkey("ctrl", "z")
        time.sleep(0.1)

    @property
    def mouse_position(self) -> tuple[int, int]:
        """Current mouse position."""
        pos = pyautogui.position()
        return (pos[0], pos[1])
