"""App Control via Terminal — open, close, fullscreen, manage windows.

Everything goes through terminal commands. Reliable, predictable, no clicking.
Every app Ghost opens goes FULLSCREEN — cleaner OCR, cleaner DOM, no clutter.

Linux (Ghost Box):   wmctrl, xdotool, xdg-open
macOS (dev/testing): osascript, open
Windows:             powershell, start
"""

import platform
import subprocess
import time
from typing import Optional

SYSTEM = platform.system()


class AppController:
    """Manage applications via terminal commands."""

    # ── Open ─────────────────────────────────────────────────────

    def open_app(self, app_name: str, fullscreen: bool = True):
        """Open an application and optionally fullscreen it."""
        if SYSTEM == "Darwin":
            subprocess.run(["open", "-a", app_name], check=False)
            time.sleep(2)
            if fullscreen:
                self._fullscreen_macos(app_name)

        elif SYSTEM == "Linux":
            # Try common launchers
            for cmd in [app_name.lower(), f"{app_name.lower()}"]:
                try:
                    subprocess.Popen(
                        [cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    time.sleep(2)
                    if fullscreen:
                        self._fullscreen_linux(app_name)
                    return
                except FileNotFoundError:
                    continue
            subprocess.run(["gtk-launch", app_name.lower()], check=False)
            time.sleep(2)
            if fullscreen:
                self._fullscreen_linux(app_name)

        elif SYSTEM == "Windows":
            subprocess.run(["start", app_name], shell=True, check=False)
            time.sleep(2)
            if fullscreen:
                self._fullscreen_windows()

    def open_url(self, url: str, browser: Optional[str] = None, fullscreen: bool = True):
        """Open a URL in a browser and fullscreen it."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if SYSTEM == "Darwin":
            if browser:
                subprocess.run(["open", "-a", browser, url], check=False)
            else:
                subprocess.run(["open", url], check=False)
            time.sleep(2)
            if fullscreen:
                # Fullscreen whichever browser opened
                target = browser or self.get_frontmost_app()
                self._fullscreen_macos(target)

        elif SYSTEM == "Linux":
            if browser:
                subprocess.Popen(
                    [browser.lower(), url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(["xdg-open", url], check=False)
            time.sleep(2)
            if fullscreen:
                self._fullscreen_linux()

        elif SYSTEM == "Windows":
            subprocess.run(["start", url], shell=True, check=False)
            time.sleep(2)
            if fullscreen:
                self._fullscreen_windows()

    # ── Close ────────────────────────────────────────────────────

    def close_app(self, app_name: str):
        """Close an application via terminal."""
        if SYSTEM == "Darwin":
            subprocess.run([
                "osascript", "-e",
                f'tell application "{app_name}" to quit'
            ], check=False, capture_output=True)

        elif SYSTEM == "Linux":
            # Try graceful close first
            subprocess.run(["wmctrl", "-c", app_name], check=False, capture_output=True)
            time.sleep(0.5)
            # If still running, kill it
            subprocess.run(
                ["pkill", "-f", app_name.lower()],
                check=False, capture_output=True,
            )

        elif SYSTEM == "Windows":
            subprocess.run(
                ["taskkill", "/IM", f"{app_name}.exe", "/F"],
                check=False, capture_output=True,
            )
        time.sleep(0.5)

    def close_current(self):
        """Close the currently focused window/app."""
        if SYSTEM == "Darwin":
            subprocess.run([
                "osascript", "-e",
                'tell application "System Events" to keystroke "q" using command down'
            ], check=False, capture_output=True)
        elif SYSTEM == "Linux":
            subprocess.run(["xdotool", "getactivewindow", "windowclose"], check=False, capture_output=True)
        elif SYSTEM == "Windows":
            subprocess.run(["powershell", "-c", "(Add-Type -A System.Windows.Forms); [System.Windows.Forms.SendKeys]::SendWait('%{F4}')"], check=False, capture_output=True)
        time.sleep(0.5)

    # ── Fullscreen ───────────────────────────────────────────────

    def fullscreen(self, app_name: Optional[str] = None):
        """Make the current or specified app fullscreen."""
        if SYSTEM == "Darwin":
            self._fullscreen_macos(app_name)
        elif SYSTEM == "Linux":
            self._fullscreen_linux(app_name)
        elif SYSTEM == "Windows":
            self._fullscreen_windows()

    def _fullscreen_macos(self, app_name: Optional[str] = None):
        """Fullscreen on macOS — maximize window to fill the entire screen.

        Uses position {0,0} + full screen size. This fills the screen
        without creating a new macOS Space (which breaks screen capture).
        """
        if app_name:
            subprocess.run([
                "osascript", "-e",
                f'tell application "{app_name}" to activate'
            ], check=False, capture_output=True)
            time.sleep(0.5)

        subprocess.run([
            "osascript", "-e",
            '''
            tell application "Finder"
                set screenBounds to bounds of window of desktop
                set screenWidth to item 3 of screenBounds
                set screenHeight to item 4 of screenBounds
            end tell
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                tell process frontApp
                    try
                        set frontWindow to window 1
                        set position of frontWindow to {0, 0}
                        set size of frontWindow to {screenWidth, screenHeight}
                    end try
                end tell
            end tell
            '''
        ], check=False, capture_output=True)
        time.sleep(0.5)

    def _fullscreen_linux(self, app_name: Optional[str] = None):
        """Fullscreen on Linux using wmctrl/xdotool."""
        if app_name:
            # Activate window by name
            subprocess.run(["wmctrl", "-a", app_name], check=False, capture_output=True)
            time.sleep(0.3)

        # Maximize the active window
        subprocess.run([
            "wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"
        ], check=False, capture_output=True)

        # Alternative: use xdotool
        subprocess.run([
            "xdotool", "key", "super+Up"  # maximize shortcut on most Linux DEs
        ], check=False, capture_output=True)
        time.sleep(0.3)

    def _fullscreen_windows(self):
        """Fullscreen on Windows."""
        subprocess.run([
            "powershell", "-c",
            "(Add-Type -A System.Windows.Forms); [System.Windows.Forms.SendKeys]::SendWait('{F11}')"
        ], check=False, capture_output=True)
        time.sleep(0.3)

    # ── Switch / Focus ───────────────────────────────────────────

    def switch_to_app(self, app_name: str, fullscreen: bool = True):
        """Bring an app to foreground and optionally fullscreen it."""
        if SYSTEM == "Darwin":
            subprocess.run([
                "osascript", "-e",
                f'tell application "{app_name}" to activate'
            ], check=False, capture_output=True)
        elif SYSTEM == "Linux":
            subprocess.run(["wmctrl", "-a", app_name], check=False, capture_output=True)
        time.sleep(0.5)

        if fullscreen:
            self.fullscreen(app_name)

    # ── Terminal Commands ────────────────────────────────────────

    def run_terminal(self, command: str, timeout: int = 30) -> str:
        """Run a terminal command and return output."""
        try:
            result = subprocess.run(
                command, shell=True,
                capture_output=True, text=True, timeout=timeout,
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error: {e}"

    # ── Query State ──────────────────────────────────────────────

    def get_frontmost_app(self) -> str:
        """Get the name of the currently focused application."""
        if SYSTEM == "Darwin":
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first application process whose frontmost is true'],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
        elif SYSTEM == "Linux":
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
        return "Unknown"

    def list_running_apps(self) -> list[str]:
        """List visible running applications."""
        if SYSTEM == "Darwin":
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of every application process whose visible is true'],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return [a.strip() for a in result.stdout.strip().split(",")]
        elif SYSTEM == "Linux":
            result = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return [line.split(None, 4)[-1] for line in result.stdout.strip().split("\n") if line]
        return []

    def is_running(self, app_name: str) -> bool:
        """Check if an app is running."""
        running = self.list_running_apps()
        return any(app_name.lower() in a.lower() for a in running)

    def get_screen_size(self) -> tuple[int, int]:
        """Get screen resolution."""
        if SYSTEM == "Darwin":
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "Finder" to get bounds of window of desktop'],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                if len(parts) == 4:
                    return (int(parts[2]), int(parts[3]))
        return (1920, 1080)
