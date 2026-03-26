"""Page Watcher — Real-time CDP event streaming.

Instead of polling (screenshot → check → repeat), Ghost listens
for page events and reacts instantly:
- Page finished loading
- DOM changed (new elements appeared)
- Navigation happened
- Dialog/alert appeared
- Download started
"""

import json
import time
import threading
from typing import Callable, Optional

from ghost.browser.cdp import BrowserController, CDPConnection


class PageWatcher:
    """Watch for browser events in real-time via CDP."""

    def __init__(self, browser: BrowserController):
        self.browser = browser
        self._callbacks: dict[str, list[Callable]] = {}
        self._watching = False
        self._thread: Optional[threading.Thread] = None

    def on(self, event: str, callback: Callable):
        """Register a callback for a CDP event.

        Events:
            "page_loaded"     — page finished loading
            "navigated"       — URL changed
            "dom_changed"     — DOM was modified
            "dialog"          — alert/confirm/prompt appeared
            "download"        — file download started
            "error"           — page error occurred
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def start(self):
        """Start watching for events in a background thread."""
        if self._watching:
            return

        cdp = self.browser._cdp
        if not cdp:
            return

        # Enable CDP event domains
        try:
            cdp.send("Page.enable")
            cdp.send("DOM.enable")
            cdp.send("Runtime.enable")
        except Exception:
            return

        self._watching = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop watching."""
        self._watching = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def wait_for_load(self, timeout: float = 15) -> bool:
        """Block until page finishes loading or timeout."""
        loaded = threading.Event()

        def on_load():
            loaded.set()

        self.on("page_loaded", on_load)

        # Also poll as fallback
        start = time.time()
        while time.time() - start < timeout:
            if loaded.is_set():
                return True

            # Check readyState as fallback
            try:
                result = self.browser._cdp.send("Runtime.evaluate", {
                    "expression": "document.readyState"
                })
                state = result.get("result", {}).get("value", "")
                if state == "complete":
                    return True
            except Exception:
                pass

            time.sleep(0.3)

        return False

    def wait_for_navigation(self, timeout: float = 10) -> Optional[str]:
        """Block until a navigation occurs. Returns new URL."""
        new_url = {"value": None}
        nav_event = threading.Event()

        def on_nav(url):
            new_url["value"] = url
            nav_event.set()

        self.on("navigated", on_nav)

        if nav_event.wait(timeout):
            return new_url["value"]
        return None

    def wait_for_element(self, selector: str, timeout: float = 10) -> bool:
        """Wait until a specific element appears in the DOM."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = self.browser._cdp.send("Runtime.evaluate", {
                    "expression": f"!!document.querySelector('{selector}')"
                })
                if result.get("result", {}).get("value"):
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def wait_for_text(self, text: str, timeout: float = 10) -> bool:
        """Wait until specific text appears on the page."""
        escaped = text.replace("'", "\\'")
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = self.browser._cdp.send("Runtime.evaluate", {
                    "expression": f"document.body.innerText.includes('{escaped}')"
                })
                if result.get("result", {}).get("value"):
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def get_page_state(self) -> dict:
        """Get current page state snapshot."""
        try:
            result = self.browser._cdp.send("Runtime.evaluate", {
                "expression": """JSON.stringify({
                    url: window.location.href,
                    title: document.title,
                    readyState: document.readyState,
                    hasAlert: !!window.__ghostAlert,
                    scrollY: window.scrollY,
                    scrollHeight: document.body.scrollHeight,
                    viewportHeight: window.innerHeight,
                })"""
            })
            return json.loads(result.get("result", {}).get("value", "{}"))
        except Exception:
            return {}

    def _watch_loop(self):
        """Background thread that listens for CDP events."""
        ws = self.browser._cdp.ws
        while self._watching:
            try:
                ws.settimeout(0.5)
                data = ws.recv()
                event = json.loads(data)
                method = event.get("method", "")

                if method == "Page.loadEventFired":
                    self._fire("page_loaded")
                elif method == "Page.frameNavigated":
                    url = event.get("params", {}).get("frame", {}).get("url", "")
                    self._fire("navigated", url)
                elif method == "DOM.documentUpdated":
                    self._fire("dom_changed")
                elif method == "Page.javascriptDialogOpening":
                    msg = event.get("params", {}).get("message", "")
                    self._fire("dialog", msg)
                elif method == "Page.downloadWillBegin":
                    self._fire("download", event.get("params", {}))
                elif method == "Runtime.exceptionThrown":
                    self._fire("error", event.get("params", {}))

            except Exception:
                pass  # timeout or connection issue

    def _fire(self, event: str, *args):
        """Fire all callbacks for an event."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args) if args else cb()
            except Exception:
                pass
