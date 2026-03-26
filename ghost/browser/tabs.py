"""Multi-Tab Awareness — Know and manage all open browser tabs.

Ghost can:
- List all tabs with titles and URLs
- Switch to a specific tab
- Find a tab by content/URL
- Close tabs
- Open new tabs
"""

import time
from typing import Optional

from ghost.browser.cdp import BrowserController, CDPConnection


class TabManager:
    """Manage browser tabs via CDP."""

    def __init__(self, browser: BrowserController):
        self.browser = browser

    def list_tabs(self) -> list[dict]:
        """List all open page tabs with titles and URLs."""
        all_targets = self.browser.list_tabs()
        tabs = []
        for i, t in enumerate(all_targets):
            if t.get("type") == "page":
                tabs.append({
                    "index": i,
                    "id": t.get("id", ""),
                    "title": t.get("title", "Untitled"),
                    "url": t.get("url", ""),
                    "ws_url": t.get("webSocketDebuggerUrl", ""),
                })
        return tabs

    def get_current_tab(self) -> Optional[dict]:
        """Get info about the currently connected tab."""
        try:
            url = self.browser.get_current_url()
            title = self.browser.get_page_title()
            return {"title": title, "url": url}
        except Exception:
            return None

    def switch_to_tab(self, tab_id: str = "", title_contains: str = "", url_contains: str = "") -> bool:
        """Switch to a tab by ID, title, or URL match."""
        tabs = self.list_tabs()

        target = None
        for tab in tabs:
            if tab_id and tab["id"] == tab_id:
                target = tab
                break
            if title_contains and title_contains.lower() in tab["title"].lower():
                target = tab
                break
            if url_contains and url_contains.lower() in tab["url"].lower():
                target = tab
                break

        if target and target.get("ws_url"):
            self.browser.disconnect()
            self.browser._cdp = CDPConnection(target["ws_url"])
            # Bring tab to front via CDP
            try:
                self.browser._cdp.send("Page.bringToFront")
            except Exception:
                pass
            time.sleep(0.5)
            return True

        return False

    def find_tab(self, query: str) -> Optional[dict]:
        """Find a tab matching a query (searches title and URL)."""
        query_lower = query.lower()
        for tab in self.list_tabs():
            if query_lower in tab["title"].lower() or query_lower in tab["url"].lower():
                return tab
        return None

    def close_tab(self, tab_id: str = "", title_contains: str = "") -> bool:
        """Close a tab by ID or title match."""
        tabs = self.list_tabs()
        for tab in tabs:
            if (tab_id and tab["id"] == tab_id) or \
               (title_contains and title_contains.lower() in tab["title"].lower()):
                target_id = tab["id"]
                try:
                    import requests
                    requests.get(
                        f"{self.browser.base_url}/json/close/{target_id}",
                        timeout=5,
                    )
                    return True
                except Exception:
                    return False
        return False

    def new_tab(self, url: str = "about:blank") -> Optional[dict]:
        """Open a new tab and switch to it."""
        tab_info = self.browser.new_tab(url)
        time.sleep(1)

        # Connect to the new tab
        tabs = self.list_tabs()
        if tabs:
            newest = tabs[-1]
            if newest.get("ws_url"):
                self.browser.disconnect()
                self.browser._cdp = CDPConnection(newest["ws_url"])
                return newest
        return tab_info

    def format_for_llm(self) -> str:
        """Format tab list for AI context."""
        tabs = self.list_tabs()
        if not tabs:
            return "No browser tabs open."

        lines = [f"OPEN TABS ({len(tabs)}):"]
        for tab in tabs:
            title = tab["title"][:50]
            url = tab["url"][:60]
            lines.append(f'  [{tab["index"]}] "{title}" | {url}')
        return "\n".join(lines)
