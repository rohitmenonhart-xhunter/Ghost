"""Unified Perception — One module to see EVERYTHING on screen.

Auto-detects the best perception method:
  Browser active? → DOM (CDP) + OCR
  Native app?     → Accessibility Tree + OCR
  Unknown?        → OCR + Grid (fallback)

All methods output the same format: a compact TEXT context for the AI.
The AI never sees screenshots — it sees structured element lists.
"""

import platform
from typing import Optional

from PIL import Image

from ghost.agent.screen import ScreenCapture
from ghost.vision.ocr import ScreenOCR, TextRegion

SYSTEM = platform.system()


class Perception:
    """Unified screen perception — the AI's eyes."""

    def __init__(
        self,
        browser=None,
        ocr: Optional[ScreenOCR] = None,
        screen: Optional[ScreenCapture] = None,
    ):
        self.browser = browser  # BrowserController (optional)
        self.ocr = ocr or ScreenOCR()
        self.screen = screen or ScreenCapture()

        # Lazy-load accessibility reader
        self._ax_reader = None

    def _get_ax_reader(self):
        if self._ax_reader is None:
            from ghost.desktop.accessibility import AccessibilityReader
            self._ax_reader = AccessibilityReader()
        return self._ax_reader

    def perceive(self) -> dict:
        """Capture complete screen state using the best available method.

        Returns:
            {
                "method": "dom" | "accessibility" | "ocr_only",
                "elements": list,       # structured elements (DOM or AX)
                "ocr_regions": list,     # OCR text regions
                "url": str,             # if browser
                "title": str,           # page/window title
                "context_for_llm": str, # compact text for AI
                "screenshot": Image,    # for fallback/grid if needed
            }
        """
        screenshot = self.screen.capture()
        result = {
            "method": "ocr_only",
            "elements": [],
            "ocr_regions": [],
            "url": "",
            "title": "",
            "context_for_llm": "",
            "screenshot": screenshot,
        }

        # Try DOM first (browser)
        dom_elements = self._try_dom(result)

        # If no DOM, try accessibility tree (native app)
        ax_elements = []
        if not dom_elements:
            ax_elements = self._try_accessibility(result)

        # Always run OCR to catch popups, overlays, and text the structure misses
        ocr_regions = self.ocr.extract(screenshot, min_confidence=0.5)
        result["ocr_regions"] = ocr_regions

        # Build unified context
        result["context_for_llm"] = self._build_context(
            dom_elements=dom_elements,
            ax_elements=ax_elements,
            ocr_regions=ocr_regions,
            url=result["url"],
            title=result["title"],
            method=result["method"],
        )

        return result

    def _try_dom(self, result: dict) -> list:
        """Try to read DOM from browser."""
        if not self.browser or not self.browser.is_available():
            return []

        try:
            self.browser.connect(0)
            result["url"] = self.browser.get_current_url()
            result["title"] = self.browser.get_page_title()
            elements = self.browser.get_interactive_elements()
            if elements:
                result["method"] = "dom"
                result["elements"] = elements
                return elements
        except Exception:
            pass
        return []

    def _try_accessibility(self, result: dict) -> list:
        """Try to read accessibility tree from the frontmost app."""
        try:
            reader = self._get_ax_reader()
            elements = reader.get_app_elements(max_elements=80, max_depth=8)
            if elements:
                result["method"] = "accessibility"
                result["elements"] = elements
                # Get window title from first window element
                for el in elements:
                    if el.role == "window" and el.name:
                        result["title"] = el.name
                        break
                return elements
        except Exception:
            pass
        return []

    def _build_context(
        self,
        dom_elements: list,
        ax_elements: list,
        ocr_regions: list,
        url: str,
        title: str,
        method: str,
    ) -> str:
        """Build compact unified context for the AI."""
        parts = []

        # Header
        if url:
            parts.append(f"PAGE: {title} | {url}")
        elif title:
            parts.append(f"APP: {title}")

        parts.append(f"METHOD: {method}")

        # DOM elements (browser)
        if dom_elements:
            parts.append(f"\nINTERACTIVE ELEMENTS ({len(dom_elements)} from DOM):")
            for el in dom_elements[:30]:
                tag = el["tag"]
                text = el.get("text", "")
                etype = el.get("type", "")
                placeholder = el.get("placeholder", "")
                visible = "visible" if el.get("visible", True) else "below fold"

                desc = f'  [{el["id"]}]* {tag}'
                if etype:
                    desc += f"[{etype}]"
                if text:
                    desc += f' "{text}"'
                if placeholder:
                    desc += f" (placeholder: {placeholder})"
                desc += f" [{visible}]"
                parts.append(desc)

        # Accessibility elements (native app)
        if ax_elements:
            parts.append(f"\nUI ELEMENTS ({len(ax_elements)} from accessibility tree):")
            for el in ax_elements:
                marker = "*" if el.clickable else " "
                desc = f"  [{el.id}]{marker} {el.role}"
                if el.name and el.name not in ("group", "split group", "scroll area"):
                    desc += f' "{el.name}"'
                if el.value:
                    desc += f' value="{el.value[:40]}"'
                if el.clickable:
                    desc += f" at ({el.x},{el.y})"
                parts.append(desc)
            parts.append("  * = clickable")

        # OCR — only show text NOT already covered by DOM/AX
        known_texts = set()
        for el in dom_elements:
            if el.get("text"):
                known_texts.add(el["text"].lower().strip()[:20])
        for el in ax_elements:
            if el.name:
                known_texts.add(el.name.lower().strip()[:20])
            if el.value:
                known_texts.add(el.value.lower().strip()[:20])

        extra_ocr = []
        for r in ocr_regions:
            text_key = r.text.lower().strip()[:20]
            if text_key not in known_texts and len(r.text.strip()) > 2:
                extra_ocr.append(r)

        if extra_ocr:
            parts.append(f"\nADDITIONAL SCREEN TEXT (OCR — popups, overlays, other windows):")
            for r in extra_ocr[:20]:
                parts.append(f'  OCR:"{r.text}" at ({r.x},{r.y})')

        # Action guide
        parts.append("\nACTIONS:")
        if dom_elements:
            parts.append("  CLICK_DOM [id] — click DOM element")
            parts.append("  FILL [id] [text] — type into DOM field")
        if ax_elements:
            parts.append("  CLICK_AX [id] — click accessibility element")
        parts.append("  CLICK_OCR [text] — click text found by OCR")
        parts.append("  TYPE [text] — type into focused field")
        parts.append("  PRESS [key] — press key (enter, tab, escape)")
        parts.append("  SCROLL [up/down] — scroll")
        parts.append("  DONE [result] — task complete")

        return "\n".join(parts)

    def find_on_screen(self, text: str) -> Optional[dict]:
        """Find any text/element on screen. Tries every method."""
        text_lower = text.lower().strip()

        # 1. Try DOM
        if self.browser and self.browser.is_available():
            try:
                elements = self.browser.get_interactive_elements()
                for el in elements:
                    if text_lower in el.get("text", "").lower():
                        return {
                            "x": el["x"], "y": el["y"],
                            "source": "dom", "element": el,
                        }
            except Exception:
                pass

        # 2. Try accessibility tree
        try:
            reader = self._get_ax_reader()
            ax_elements = reader.get_app_elements(max_elements=80)
            for el in ax_elements:
                if text_lower in el.name.lower() or text_lower in el.value.lower():
                    return {
                        "x": el.x, "y": el.y,
                        "source": "accessibility", "element": el,
                    }
        except Exception:
            pass

        # 3. Try OCR
        screenshot = self.screen.capture()
        region = self.ocr.find_text(screenshot, text)
        if region:
            return {
                "x": region.x, "y": region.y,
                "source": "ocr", "region": region,
            }

        return None
