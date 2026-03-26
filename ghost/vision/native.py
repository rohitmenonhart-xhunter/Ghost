"""Native App Perception — OCR + single dense grid + VLM for non-browser apps.

For apps without DOM access (Finder, Terminal, Photoshop, etc.):
1. Screenshot the fullscreen app
2. RapidOCR extracts all text with bboxes
3. Dense grid overlay (10x8 = 80 cells) in a single layer
4. Combine OCR text + grid labels → send to AI as TEXT (not image)
5. AI picks: "click OCR text 'Save'" or "click grid cell F3"

One screenshot, one AI call, precise clicking.
"""

from typing import Optional
from PIL import Image

from ghost.vision.ocr import ScreenOCR, TextRegion
from ghost.vision.grid import GridOverlay
from ghost.agent.screen import ScreenCapture


class NativeAppPerception:
    """Perceive native apps via OCR + dense grid."""

    def __init__(
        self,
        ocr: Optional[ScreenOCR] = None,
        screen: Optional[ScreenCapture] = None,
        grid_cols: int = 10,
        grid_rows: int = 8,
    ):
        self.ocr = ocr or ScreenOCR()
        self.screen = screen or ScreenCapture()
        self.grid = GridOverlay(cols=grid_cols, rows=grid_rows, label_size=14)

    def perceive(self) -> dict:
        """Capture and analyze the current native app screen.

        Returns:
            {
                "screenshot": PIL Image,
                "gridded": PIL Image (with grid overlay),
                "ocr_regions": list of TextRegion,
                "context_for_llm": str (compact text for AI),
                "grid": GridOverlay (for coordinate lookup),
            }
        """
        screenshot = self.screen.capture()
        gridded = self.grid.overlay(screenshot)
        ocr_regions = self.ocr.extract(screenshot, min_confidence=0.5)

        context = self._build_context(ocr_regions, screenshot.size)

        return {
            "screenshot": screenshot,
            "gridded": gridded,
            "ocr_regions": ocr_regions,
            "context_for_llm": context,
            "grid": self.grid,
        }

    def _build_context(self, regions: list[TextRegion], img_size: tuple[int, int]) -> str:
        """Build compact context combining OCR text + grid positions."""
        w, h = img_size
        cell_w = w / self.grid.cols
        cell_h = h / self.grid.rows

        parts = []
        parts.append(f"SCREEN: {w}x{h} | Grid: {self.grid.cols}x{self.grid.rows}")
        parts.append(f"Grid labels: {', '.join(self.grid.get_all_labels())}")
        parts.append("")

        if regions:
            parts.append("VISIBLE TEXT (OCR — with position and grid cell):")
            for r in sorted(regions, key=lambda r: (r.y1, r.x1))[:50]:
                # Map OCR position to grid cell
                col = min(int(r.x / cell_w), self.grid.cols - 1)
                row = min(int(r.y / cell_h), self.grid.rows - 1)
                cell = self.grid.cell_label(col, row)

                parts.append(
                    f'  "{r.text}" at ({r.x},{r.y}) [cell {cell}]'
                )
        else:
            parts.append("No text detected on screen.")

        parts.append("")
        parts.append("TO CLICK: use either 'CLICK_OCR [text]' or 'CLICK_GRID [cell]'")

        return "\n".join(parts)

    def find_text(self, target: str) -> Optional[dict]:
        """Find text on the native app screen."""
        screenshot = self.screen.capture()
        region = self.ocr.find_text(screenshot, target)
        if region:
            return {"x": region.x, "y": region.y, "text": region.text, "source": "ocr"}
        return None

    def grid_center(self, cell_label: str, img_size: tuple[int, int]) -> Optional[tuple[int, int]]:
        """Get pixel coordinates for a grid cell center."""
        parsed = self.grid.parse_label(cell_label)
        if parsed is None:
            return None
        col, row = parsed
        return self.grid.cell_center(col, row, img_size)
