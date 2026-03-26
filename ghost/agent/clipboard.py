"""Clipboard Bridge — Read/write clipboard across apps.

Ghost uses clipboard to transfer data between applications:
- Copy text from a webpage → paste into a spreadsheet
- Copy a file path → paste into terminal
- Read clipboard content to understand what user copied
"""

import platform
import subprocess
from typing import Optional

SYSTEM = platform.system()


class Clipboard:
    """Cross-platform clipboard read/write."""

    def copy(self, text: str):
        """Copy text to system clipboard."""
        if SYSTEM == "Darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
        elif SYSTEM == "Linux":
            try:
                p = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                )
                p.communicate(text.encode("utf-8"))
            except FileNotFoundError:
                p = subprocess.Popen(
                    ["xsel", "--clipboard", "--input"],
                    stdin=subprocess.PIPE,
                )
                p.communicate(text.encode("utf-8"))
        elif SYSTEM == "Windows":
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-16-le"))

    def paste(self) -> str:
        """Read text from system clipboard."""
        if SYSTEM == "Darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True)
            return result.stdout
        elif SYSTEM == "Linux":
            try:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True, text=True,
                )
                return result.stdout
            except FileNotFoundError:
                result = subprocess.run(
                    ["xsel", "--clipboard", "--output"],
                    capture_output=True, text=True,
                )
                return result.stdout
        elif SYSTEM == "Windows":
            result = subprocess.run(
                ["powershell", "-c", "Get-Clipboard"],
                capture_output=True, text=True,
            )
            return result.stdout
        return ""

    def clear(self):
        """Clear the clipboard."""
        self.copy("")

    def has_text(self) -> bool:
        """Check if clipboard has text content."""
        return len(self.paste().strip()) > 0

    def copy_from_app(self):
        """Trigger Cmd+C / Ctrl+C in the active app to copy selection."""
        import pyautogui
        if SYSTEM == "Darwin":
            pyautogui.hotkey("command", "c")
        else:
            pyautogui.hotkey("ctrl", "c")
        import time
        time.sleep(0.2)

    def paste_to_app(self):
        """Trigger Cmd+V / Ctrl+V in the active app to paste."""
        import pyautogui
        if SYSTEM == "Darwin":
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")
        import time
        time.sleep(0.2)

    def copy_and_read(self) -> str:
        """Copy current selection in active app and return the text."""
        self.copy_from_app()
        import time
        time.sleep(0.2)
        return self.paste()
