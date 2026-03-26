"""Accessibility Tree Reader — The DOM equivalent for native apps.

macOS: AXUIElement API (ApplicationServices)
Linux: AT-SPI (pyatspi2) — for Ghost Box
Windows: UIA (comtypes/uiautomation)

Reads the ENTIRE UI structure of any running app:
buttons, menus, text fields, labels, toolbars — all with exact positions.
Combined with OCR, gives complete understanding without screenshots.
"""

import platform
import subprocess
from dataclasses import dataclass, field
from typing import Optional

SYSTEM = platform.system()


@dataclass
class UIElement:
    """A single UI element from the accessibility tree."""
    id: int
    role: str           # button, text_field, menu_item, static_text, etc.
    name: str           # element label/title
    value: str          # current value (for text fields, checkboxes, etc.)
    x: int              # center x position
    y: int              # center y position
    width: int
    height: int
    clickable: bool     # can this be interacted with?
    children_count: int
    depth: int          # depth in the tree


class AccessibilityReader:
    """Read the accessibility tree of any running app."""

    def __init__(self):
        self._element_id = 0

    def get_app_elements(self, pid: Optional[int] = None, max_elements: int = 100, max_depth: int = 8) -> list[UIElement]:
        """Get all interactive elements from an app's accessibility tree.

        Args:
            pid: Process ID. If None, uses the frontmost app.
            max_elements: Cap on elements to return (prevent explosion on complex apps)
            max_depth: How deep to traverse the tree
        """
        if SYSTEM == "Darwin":
            return self._read_macos(pid, max_elements, max_depth)
        elif SYSTEM == "Linux":
            return self._read_linux(pid, max_elements, max_depth)
        else:
            return []

    def get_frontmost_pid(self) -> int:
        """Get PID of the frontmost application."""
        if SYSTEM == "Darwin":
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get unix id of first application process whose frontmost is true'],
                capture_output=True, text=True, timeout=5,
            )
            return int(result.stdout.strip())
        elif SYSTEM == "Linux":
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowpid"],
                capture_output=True, text=True, timeout=5,
            )
            return int(result.stdout.strip())
        return 0

    # ── macOS (AXUIElement) ──────────────────────────────────────

    def _read_macos(self, pid: Optional[int], max_elements: int, max_depth: int) -> list[UIElement]:
        from ApplicationServices import (
            AXUIElementCreateApplication,
            AXUIElementCopyAttributeValue,
        )

        if pid is None:
            pid = self.get_frontmost_pid()

        app = AXUIElementCreateApplication(pid)
        self._element_id = 0
        elements = []
        self._walk_macos(app, elements, max_elements, max_depth, depth=0)
        return elements

    def _walk_macos(self, element, results: list, max_elements: int, max_depth: int, depth: int):
        """Recursively walk the macOS accessibility tree."""
        if len(results) >= max_elements or depth > max_depth:
            return

        from ApplicationServices import AXUIElementCopyAttributeValue

        # Read attributes — try multiple name sources
        role = self._ax_get(element, "AXRole") or ""
        name = (
            self._ax_get(element, "AXTitle")
            or self._ax_get(element, "AXDescription")
            or self._ax_get(element, "AXLabel")
            or self._ax_get(element, "AXHelp")
            or ""
        )
        value = self._ax_get(element, "AXValue") or ""
        role_desc = self._ax_get(element, "AXRoleDescription") or ""
        # Use role description as name fallback
        if not name and role_desc:
            name = role_desc

        # Get position and size via string parsing (pyobjc AXValue workaround)
        import re as _re
        pos_raw = self._ax_get(element, "AXPosition")
        size_raw = self._ax_get(element, "AXSize")

        x, y, w, h = 0, 0, 0, 0
        if pos_raw:
            m = _re.search(r"x:([\d.]+).*?y:([\d.]+)", str(pos_raw))
            if m:
                x, y = int(float(m.group(1))), int(float(m.group(2)))
        if size_raw:
            m = _re.search(r"w:([\d.]+).*?h:([\d.]+)", str(size_raw))
            if m:
                w, h = int(float(m.group(1))), int(float(m.group(2)))

        # Determine if clickable
        clickable = role in (
            "AXButton", "AXMenuItem", "AXMenuBarItem", "AXLink",
            "AXPopUpButton", "AXCheckBox", "AXRadioButton", "AXComboBox",
            "AXTab", "AXCell", "AXImage", "AXToolbar", "AXSlider",
            "AXIncrementor", "AXColorWell", "AXDisclosureTriangle",
            "AXStaticText", "AXHeading",
        )

        # Also clickable if it has AXPress action
        actions = self._ax_get(element, "AXActions")
        if actions and "AXPress" in list(actions or []):
            clickable = True

        # Text fields are interactive
        is_text_field = role in ("AXTextField", "AXTextArea", "AXComboBox", "AXSearchField")
        if is_text_field:
            clickable = True

        # Get children count
        children = self._ax_get(element, "AXChildren") or []
        children_count = len(children) if children else 0

        # Simplify role name
        simple_role = role.replace("AX", "").lower() if role else "unknown"

        # Include elements that are named, interactive, or structural
        has_name = bool(name) or bool(value)
        is_interactive = clickable or is_text_field
        is_visible = w > 5 and h > 5
        is_structural = role in ("AXMenuBar", "AXToolbar", "AXGroup", "AXTabGroup", "AXWindow")

        if (has_name or is_interactive) and is_visible:
            self._element_id += 1
            results.append(UIElement(
                id=self._element_id,
                role=simple_role,
                name=str(name)[:80],
                value=str(value)[:80] if value else "",
                x=x + w // 2,  # center
                y=y + h // 2,
                width=w,
                height=h,
                clickable=is_interactive,
                children_count=children_count,
                depth=depth,
            ))

        # Recurse into children
        if children:
            for child in children:
                if len(results) >= max_elements:
                    break
                self._walk_macos(child, results, max_elements, max_depth, depth + 1)

    @staticmethod
    def _ax_get(element, attribute: str):
        """Get an accessibility attribute value. Returns None on failure."""
        from ApplicationServices import AXUIElementCopyAttributeValue
        try:
            err, value = AXUIElementCopyAttributeValue(element, attribute, None)
            if err == 0:
                return value
        except Exception:
            pass
        return None

    # ── Linux (AT-SPI) ───────────────────────────────────────────

    def _read_linux(self, pid: Optional[int], max_elements: int, max_depth: int) -> list[UIElement]:
        """Read AT-SPI tree on Linux. Used on the Ghost Box."""
        try:
            import pyatspi
        except ImportError:
            return []

        desktop = pyatspi.Registry.getDesktop(0)
        self._element_id = 0
        elements = []

        for app in desktop:
            if pid and app.get_process_id() != pid:
                continue
            if not pid:
                # Use active app
                pass
            self._walk_linux(app, elements, max_elements, max_depth, depth=0)

        return elements

    def _walk_linux(self, node, results: list, max_elements: int, max_depth: int, depth: int):
        if len(results) >= max_elements or depth > max_depth:
            return

        try:
            import pyatspi

            role = node.getRoleName()
            name = node.name or ""
            value = ""

            # Get value for text fields
            try:
                text_iface = node.queryText()
                if text_iface:
                    value = text_iface.getText(0, -1)[:80]
            except Exception:
                pass

            # Get position
            try:
                component = node.queryComponent()
                bbox = component.getExtents(pyatspi.DESKTOP_COORDS)
                x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height
            except Exception:
                x, y, w, h = 0, 0, 0, 0

            clickable = role in (
                "push button", "menu item", "link", "check box",
                "radio button", "combo box", "tab", "toggle button",
                "spin button", "slider",
            )
            is_text = role in ("text", "entry", "password text")
            if is_text:
                clickable = True

            is_visible = w > 5 and h > 5
            has_name = bool(name) or bool(value)

            if (has_name or clickable or is_text) and is_visible:
                self._element_id += 1
                results.append(UIElement(
                    id=self._element_id,
                    role=role.replace(" ", "_"),
                    name=name[:80],
                    value=value[:80],
                    x=x + w // 2,
                    y=y + h // 2,
                    width=w,
                    height=h,
                    clickable=clickable or is_text,
                    children_count=node.childCount,
                    depth=depth,
                ))

            for i in range(node.childCount):
                if len(results) >= max_elements:
                    break
                try:
                    child = node.getChildAtIndex(i)
                    if child:
                        self._walk_linux(child, results, max_elements, max_depth, depth + 1)
                except Exception:
                    continue

        except Exception:
            pass

    # ── Formatting ───────────────────────────────────────────────

    def format_for_llm(self, elements: list[UIElement]) -> str:
        """Format accessibility elements as compact text for the AI."""
        if not elements:
            return "No UI elements found."

        lines = [f"UI ELEMENTS ({len(elements)} found):"]
        for el in elements:
            marker = "*" if el.clickable else " "
            desc = f"  [{el.id}]{marker} {el.role}"
            if el.name:
                desc += f' "{el.name}"'
            if el.value:
                desc += f" value=\"{el.value}\""
            if el.clickable:
                desc += f" at ({el.x},{el.y})"
            lines.append(desc)

        lines.append("")
        lines.append("  * = clickable/interactive")
        return "\n".join(lines)
