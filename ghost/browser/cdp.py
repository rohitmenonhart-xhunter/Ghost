"""Chrome DevTools Protocol — Control the user's REAL browser.

No sandboxed Playwright window. Connects to the user's running Chrome/Brave/Edge
with all their cookies, saved passwords, and login sessions.

Platform support:
  Linux (primary):   google-chrome --remote-debugging-port=9222
  Windows:           chrome.exe --remote-debugging-port=9222
  macOS (fallback):  Needs profile workaround — use grid method or AppleScript instead.

On the Ghost Box (Linux), Chrome is launched with CDP from boot. No conflicts.
"""

import json
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests
import websocket


SYSTEM = platform.system()

# Default Chrome paths per platform
CHROME_PATHS = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "Linux": [
        "google-chrome", "google-chrome-stable",
        "brave-browser", "chromium-browser", "chromium",
        "microsoft-edge",
    ],
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
}

# Default profile paths
CHROME_PROFILES = {
    "Darwin": str(Path.home() / "Library/Application Support/Google/Chrome"),
    "Linux": str(Path.home() / ".config/google-chrome"),
    "Windows": str(Path.home() / r"AppData\Local\Google\Chrome\User Data"),
}

CDP_PORT = 9222


class CDPConnection:
    """Raw CDP websocket connection to a browser tab."""

    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=10)
        self._msg_id = 0

    def send(self, method: str, params: Optional[dict] = None) -> dict:
        """Send a CDP command and wait for response."""
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params

        self.ws.send(json.dumps(msg))

        # Wait for matching response
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self._msg_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP error: {resp['error']}")
                return resp.get("result", {})

    def close(self):
        self.ws.close()


class BrowserController:
    """Control the user's real browser via CDP."""

    def __init__(self, port: int = CDP_PORT):
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self._cdp: Optional[CDPConnection] = None

    # ── Connection ───────────────────────────────────────────────

    def is_available(self) -> bool:
        """Check if a CDP-enabled browser is running."""
        try:
            r = requests.get(f"{self.base_url}/json/version", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def launch_with_debugging(self, chrome_path: Optional[str] = None, profile_dir: Optional[str] = None):
        """Launch Chrome with remote debugging.

        On Linux/Windows: uses the default profile directly — just works.
        On macOS: Chrome locks the default profile, so we create a symlinked
                  profile dir as a workaround for local dev/testing.
        """
        if self.is_available():
            print("  [Browser] Already running with CDP enabled.")
            return

        # Find Chrome
        if chrome_path is None:
            for path in CHROME_PATHS.get(SYSTEM, []):
                if Path(path).exists() or self._which(path):
                    chrome_path = path
                    break

        if chrome_path is None:
            raise FileNotFoundError("Could not find Chrome/Chromium. Install Chrome or specify path.")

        # Determine profile directory
        if profile_dir is None:
            if SYSTEM == "Darwin":
                # macOS workaround: Chrome won't allow CDP on default profile dir.
                # Create a separate dir that copies cookies from the real profile.
                real_profile = Path(CHROME_PROFILES["Darwin"])
                ghost_profile = Path.home() / ".ghost" / "chrome-profile"
                ghost_profile.mkdir(parents=True, exist_ok=True)

                # Copy key files for login persistence (cookies, login data)
                default_dir = real_profile / "Default"
                ghost_default = ghost_profile / "Default"
                ghost_default.mkdir(exist_ok=True)

                for fname in ["Cookies", "Login Data", "Web Data", "Preferences",
                              "Bookmarks", "Favicons", "History"]:
                    src = default_dir / fname
                    dst = ghost_default / fname
                    if src.exists() and not dst.exists():
                        try:
                            import shutil
                            shutil.copy2(src, dst)
                        except Exception:
                            pass

                # Also copy Local State
                local_state = real_profile / "Local State"
                if local_state.exists():
                    dst = ghost_profile / "Local State"
                    if not dst.exists():
                        try:
                            import shutil
                            shutil.copy2(local_state, dst)
                        except Exception:
                            pass

                profile_dir = str(ghost_profile)
                print(f"  [Browser] macOS: using ghost profile at {profile_dir}")
            else:
                # Linux/Windows: use default profile directly — no conflicts
                profile_dir = CHROME_PROFILES.get(SYSTEM, "")

        cmd = [chrome_path, f"--remote-debugging-port={self.port}", "--remote-allow-origins=*"]

        if profile_dir and Path(profile_dir).exists():
            cmd.append(f"--user-data-dir={profile_dir}")

        print(f"  [Browser] Launching: {Path(chrome_path).name} with CDP on port {self.port}")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for it to be ready
        for _ in range(30):
            if self.is_available():
                print("  [Browser] Ready.")
                return
            time.sleep(0.5)

        raise TimeoutError("Browser did not start with CDP in time.")

    def connect(self, tab_index: int = 0):
        """Connect to a browser tab."""
        tabs = self.list_tabs()
        if not tabs:
            raise ConnectionError("No browser tabs found. Is Chrome running with --remote-debugging-port?")

        # Find a real page tab (not devtools, extensions, etc.)
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if not page_tabs:
            page_tabs = tabs

        target = page_tabs[min(tab_index, len(page_tabs) - 1)]
        ws_url = target["webSocketDebuggerUrl"]

        self._cdp = CDPConnection(ws_url)
        return target

    def disconnect(self):
        if self._cdp:
            self._cdp.close()
            self._cdp = None

    # ── Tab Management ───────────────────────────────────────────

    def list_tabs(self) -> list[dict]:
        """List all open browser tabs."""
        try:
            r = requests.get(f"{self.base_url}/json", timeout=5)
            return r.json()
        except Exception:
            return []

    def get_current_url(self) -> str:
        """Get URL of the connected tab."""
        result = self._cdp.send("Runtime.evaluate", {
            "expression": "window.location.href"
        })
        return result.get("result", {}).get("value", "")

    def get_page_title(self) -> str:
        """Get title of the connected tab."""
        result = self._cdp.send("Runtime.evaluate", {
            "expression": "document.title"
        })
        return result.get("result", {}).get("value", "")

    def navigate(self, url: str):
        """Navigate to a URL."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self._cdp.send("Page.navigate", {"url": url})
        time.sleep(2)  # wait for load

    def new_tab(self, url: str = "about:blank") -> dict:
        """Open a new tab."""
        r = requests.get(f"{self.base_url}/json/new?{url}", timeout=5)
        return r.json()

    def close_tab(self, tab_id: Optional[str] = None):
        """Close a tab."""
        if tab_id:
            requests.get(f"{self.base_url}/json/close/{tab_id}", timeout=5)

    # ── DOM Reading ──────────────────────────────────────────────

    def get_interactive_elements(self) -> list[dict]:
        """Get all clickable/interactive elements with their positions.

        This is the core function. Returns a list like:
        [
            {"id": 1, "tag": "button", "text": "Log In", "x": 540, "y": 320, "w": 80, "h": 32, "selector": "..."},
            {"id": 2, "tag": "input", "type": "email", "placeholder": "Email", "x": 400, "y": 450, ...},
        ]
        """
        js = """
        (() => {
            const selectors = 'a, button, input, select, textarea, [role="button"], [onclick], [tabindex], label[for], summary';
            const elements = document.querySelectorAll(selectors);
            const results = [];
            let id = 1;

            for (const el of elements) {
                const rect = el.getBoundingClientRect();

                // Skip hidden/off-screen elements
                if (rect.width === 0 || rect.height === 0) continue;
                if (rect.top > window.innerHeight + 500) continue; // skip far below fold
                if (rect.bottom < -500) continue;

                const text = (el.textContent || '').trim().slice(0, 80);
                const ariaLabel = el.getAttribute('aria-label') || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const type = el.getAttribute('type') || '';
                const href = el.getAttribute('href') || '';
                const role = el.getAttribute('role') || '';
                const name = el.getAttribute('name') || '';
                const value = el.value || '';

                // Build a display label
                let label = text || ariaLabel || placeholder || name || type || el.tagName.toLowerCase();

                // Build a unique CSS selector
                let selector = '';
                if (el.id) {
                    selector = '#' + el.id;
                } else if (el.name) {
                    selector = `${el.tagName.toLowerCase()}[name="${el.name}"]`;
                } else if (text && el.tagName === 'BUTTON') {
                    selector = `button:has-text("${text.slice(0, 30)}")`;
                } else if (ariaLabel) {
                    selector = `[aria-label="${ariaLabel}"]`;
                }

                results.push({
                    id: id++,
                    tag: el.tagName.toLowerCase(),
                    text: label.slice(0, 60),
                    type: type,
                    placeholder: placeholder,
                    href: href ? href.slice(0, 100) : '',
                    role: role,
                    x: Math.round(rect.left + rect.width / 2),
                    y: Math.round(rect.top + rect.height / 2),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    visible: rect.top >= 0 && rect.top <= window.innerHeight,
                    selector: selector,
                });
            }

            return JSON.stringify(results);
        })()
        """

        result = self._cdp.send("Runtime.evaluate", {"expression": js})
        raw = result.get("result", {}).get("value", "[]")
        return json.loads(raw)

    def get_page_text(self) -> str:
        """Get visible text content of the page."""
        result = self._cdp.send("Runtime.evaluate", {
            "expression": "document.body.innerText.slice(0, 5000)"
        })
        return result.get("result", {}).get("value", "")

    # ── Interaction ──────────────────────────────────────────────

    def click_element(self, selector: str):
        """Click an element by CSS selector."""
        js = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (el) {{ el.click(); return true; }}
            return false;
        }})()
        """
        result = self._cdp.send("Runtime.evaluate", {"expression": js})
        return result.get("result", {}).get("value", False)

    def click_by_text(self, text: str, tag: str = "*"):
        """Click an element by its text content."""
        js = f"""
        (() => {{
            const els = document.querySelectorAll('{tag}');
            for (const el of els) {{
                if (el.textContent.trim().includes('{text}')) {{
                    el.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
        result = self._cdp.send("Runtime.evaluate", {"expression": js})
        return result.get("result", {}).get("value", False)

    def click_at(self, x: int, y: int):
        """Click at specific coordinates using CDP Input events."""
        self._cdp.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })
        self._cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })

    def type_text(self, text: str):
        """Type text into the currently focused element."""
        for char in text:
            self._cdp.send("Input.dispatchKeyEvent", {
                "type": "keyDown", "text": char,
            })
            self._cdp.send("Input.dispatchKeyEvent", {
                "type": "keyUp", "text": char,
            })

    def fill_field(self, selector: str, value: str):
        """Focus a field and set its value."""
        js = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return false;
            el.focus();
            el.value = '{value}';
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()
        """
        result = self._cdp.send("Runtime.evaluate", {"expression": js})
        return result.get("result", {}).get("value", False)

    def press_key(self, key: str):
        """Press a keyboard key (Enter, Tab, Escape, etc.)."""
        key_map = {
            "enter": {"key": "Enter", "code": "Enter", "keyCode": 13},
            "tab": {"key": "Tab", "code": "Tab", "keyCode": 9},
            "escape": {"key": "Escape", "code": "Escape", "keyCode": 27},
            "backspace": {"key": "Backspace", "code": "Backspace", "keyCode": 8},
        }
        kinfo = key_map.get(key.lower(), {"key": key, "code": key, "keyCode": 0})

        self._cdp.send("Input.dispatchKeyEvent", {
            "type": "keyDown", **kinfo, "windowsVirtualKeyCode": kinfo["keyCode"],
        })
        self._cdp.send("Input.dispatchKeyEvent", {
            "type": "keyUp", **kinfo, "windowsVirtualKeyCode": kinfo["keyCode"],
        })

    # ── Scrolling ────────────────────────────────────────────────

    def scroll(self, direction: str = "down", amount: int = 500):
        """Scroll the page."""
        delta = -amount if direction == "up" else amount
        self._cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseWheel", "x": 400, "y": 400,
            "deltaX": 0, "deltaY": delta,
        })
        time.sleep(0.5)

    def scroll_to_element(self, selector: str):
        """Scroll an element into view."""
        js = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (el) {{ el.scrollIntoView({{ behavior: 'smooth', block: 'center' }}); return true; }}
            return false;
        }})()
        """
        self._cdp.send("Runtime.evaluate", {"expression": js})
        time.sleep(1)

    def scroll_to_text(self, text: str):
        """Scroll to an element containing specific text."""
        js = f"""
        (() => {{
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {{
                if (walker.currentNode.textContent.includes('{text}')) {{
                    walker.currentNode.parentElement.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    return true;
                }}
            }}
            return false;
        }})()
        """
        self._cdp.send("Runtime.evaluate", {"expression": js})
        time.sleep(1)

    def get_scroll_position(self) -> dict:
        """Get current scroll position and page dimensions."""
        result = self._cdp.send("Runtime.evaluate", {
            "expression": "JSON.stringify({scrollY: window.scrollY, scrollHeight: document.body.scrollHeight, viewportHeight: window.innerHeight})"
        })
        return json.loads(result.get("result", {}).get("value", "{}"))

    # ── Utils ────────────────────────────────────────────────────

    @staticmethod
    def _which(name: str) -> Optional[str]:
        """Find executable in PATH."""
        try:
            result = subprocess.run(["which", name], capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def format_elements_for_vlm(self, elements: list[dict], max_elements: int = 30) -> str:
        """Format interactive elements as a compact text list for the VLM.

        This is what makes it cheap: instead of sending a screenshot,
        we send ~300 tokens of text describing what's on screen.
        """
        # Filter to visible elements and limit count
        visible = [e for e in elements if e.get("visible", True)]
        visible = visible[:max_elements]

        if not visible:
            return "No interactive elements found on page."

        lines = []
        for el in visible:
            tag = el["tag"]
            text = el["text"]
            etype = el.get("type", "")
            placeholder = el.get("placeholder", "")
            href = el.get("href", "")

            desc = f'[{el["id"]}] {tag}'
            if etype:
                desc += f'[{etype}]'
            if text:
                desc += f' "{text}"'
            if placeholder:
                desc += f' (placeholder: {placeholder})'
            if href and len(href) < 60:
                desc += f' → {href}'

            lines.append(desc)

        return "\n".join(lines)
