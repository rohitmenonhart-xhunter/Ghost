"""Grid Engine — Overlay labeled grids on screenshots for VLM grounding.

Key design: when zooming into small regions, UPSCALE them before gridding
so the VLM can actually see the content underneath the labels.
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Optional

COL_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font, falling back gracefully."""
    paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


class GridOverlay:
    """Draws a labeled grid on an image."""

    def __init__(
        self,
        cols: int = 6,
        rows: int = 4,
        line_color: tuple = (255, 0, 0),
        line_width: int = 2,
        label_size: int = 16,
        label_color: tuple = (255, 255, 255),
        label_bg: tuple = (255, 0, 0),
        label_opacity: int = 200,
    ):
        self.cols = cols
        self.rows = rows
        self.line_color = line_color
        self.line_width = line_width
        self.label_size = label_size
        self.label_color = label_color
        self.label_bg = label_bg
        self.label_opacity = label_opacity

    def overlay(self, image: Image.Image, min_display_size: int = 400) -> Image.Image:
        """Draw grid with labels on the image.

        If the image is too small, upscales it first so grid labels
        don't obscure the content.
        """
        img = image.copy().convert("RGBA")

        # Upscale small images so content stays visible under labels
        scale = 1.0
        if img.width < min_display_size or img.height < min_display_size:
            scale = max(min_display_size / img.width, min_display_size / img.height)
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        w, h = img.size
        cell_w = w / self.cols
        cell_h = h / self.rows

        # Create transparent overlay for labels
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw grid lines
        for col in range(1, self.cols):
            x = int(col * cell_w)
            draw.line([(x, 0), (x, h)], fill=self.line_color + (200,), width=self.line_width)
        for row in range(1, self.rows):
            y = int(row * cell_h)
            draw.line([(0, y), (w, y)], fill=self.line_color + (200,), width=self.line_width)

        # Draw border
        draw.rectangle([0, 0, w - 1, h - 1], outline=self.line_color + (200,), width=self.line_width)

        # Adaptive label size based on cell dimensions
        effective_label_size = min(self.label_size, int(cell_w * 0.3), int(cell_h * 0.3))
        effective_label_size = max(effective_label_size, 10)
        font = _get_font(effective_label_size)

        # Draw labels at top-left corner of each cell (not center — less obstruction)
        for row in range(self.rows):
            for col in range(self.cols):
                label = self.cell_label(col, row)
                x1 = int(col * cell_w)
                y1 = int(row * cell_h)

                bbox = font.getbbox(label)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                pad = 3

                # Background pill at top-left corner
                bg_rect = [
                    x1 + 2, y1 + 2,
                    x1 + tw + pad * 2 + 2, y1 + th + pad * 2 + 2,
                ]
                draw.rectangle(bg_rect, fill=self.label_bg + (self.label_opacity,))
                draw.text(
                    (x1 + pad + 2, y1 + pad + 2),
                    label, fill=self.label_color + (255,), font=font,
                )

        # Composite
        result = Image.alpha_composite(img, overlay).convert("RGB")
        return result

    def cell_label(self, col: int, row: int) -> str:
        return f"{COL_LABELS[col]}{row + 1}"

    def parse_label(self, label: str) -> Optional[tuple[int, int]]:
        """Parse label → (col, row) indices."""
        label = label.strip().upper()
        if len(label) < 2:
            return None
        col_char = label[0]
        row_str = label[1:]
        if col_char not in COL_LABELS:
            return None
        try:
            col = COL_LABELS.index(col_char)
            row = int(row_str) - 1
        except (ValueError, IndexError):
            return None
        if col >= self.cols or row >= self.rows or row < 0:
            return None
        return (col, row)

    def cell_bounds(self, col: int, row: int, image_size: tuple[int, int]) -> tuple[int, int, int, int]:
        """Pixel bounds (x1, y1, x2, y2) in original image coordinates."""
        w, h = image_size
        cell_w = w / self.cols
        cell_h = h / self.rows
        return (
            int(col * cell_w),
            int(row * cell_h),
            int((col + 1) * cell_w),
            int((row + 1) * cell_h),
        )

    def cell_center(self, col: int, row: int, image_size: tuple[int, int]) -> tuple[int, int]:
        x1, y1, x2, y2 = self.cell_bounds(col, row, image_size)
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def crop_cell(self, image: Image.Image, col: int, row: int) -> Image.Image:
        return image.crop(self.cell_bounds(col, row, image.size))

    def get_all_labels(self) -> list[str]:
        return [
            self.cell_label(col, row)
            for row in range(self.rows)
            for col in range(self.cols)
        ]


class RecursiveGrid:
    """Recursive zoom: narrows to exact pixel coordinates in 2-3 rounds.

    Each round: overlay grid → VLM picks cell → crop cell → repeat.
    Small crops are upscaled so the VLM can see the content.
    """

    def __init__(self, level_configs: Optional[list[dict]] = None):
        self.level_configs = level_configs or [
            {"cols": 8, "rows": 5, "label_size": 18},   # L0: ~215x216px cells
            {"cols": 5, "rows": 5, "label_size": 16},   # L1: ~43x43px cells (precise enough for dock icons)
            {"cols": 3, "rows": 3, "label_size": 14},   # L2: ~14x14px (pixel-perfect)
        ]
        self.grids = [GridOverlay(**cfg) for cfg in self.level_configs]

        self._level = 0
        self._offset_x = 0
        self._offset_y = 0

    @property
    def max_levels(self) -> int:
        return len(self.grids)

    @property
    def current_level(self) -> int:
        return self._level

    def reset(self):
        self._level = 0
        self._offset_x = 0
        self._offset_y = 0

    def get_gridded_image(self, image: Image.Image) -> Image.Image:
        """Get image with grid overlay at current level."""
        if self._level >= self.max_levels:
            return image
        return self.grids[self._level].overlay(image)

    def process_selection(self, label: str, image: Image.Image) -> dict:
        """Process VLM's cell selection, return coordinates or zoom request."""
        if self._level >= self.max_levels:
            return {"coordinates": None, "needs_zoom": False, "zoomed_image": None,
                    "level": self._level, "cell_label": label}

        grid = self.grids[self._level]
        parsed = grid.parse_label(label)

        if parsed is None:
            return {"coordinates": None, "needs_zoom": False, "zoomed_image": None,
                    "level": self._level, "cell_label": label}

        col, row = parsed
        bounds = grid.cell_bounds(col, row, image.size)
        center = grid.cell_center(col, row, image.size)

        # Absolute coordinates in original screen space
        abs_x = self._offset_x + center[0]
        abs_y = self._offset_y + center[1]

        cell_w = bounds[2] - bounds[0]
        cell_h = bounds[3] - bounds[1]

        # Stop zooming if cell is small enough or last level
        if cell_w < 50 or cell_h < 40 or self._level >= self.max_levels - 1:
            self.reset()
            return {
                "coordinates": (abs_x, abs_y),
                "needs_zoom": False,
                "zoomed_image": None,
                "level": self._level,
                "cell_label": label,
            }

        # Crop and prepare for next level
        cropped = image.crop(bounds)

        self._offset_x += bounds[0]
        self._offset_y += bounds[1]
        self._level += 1

        # Get gridded version of zoomed region (auto-upscales if small)
        next_gridded = None
        if self._level < self.max_levels:
            next_gridded = self.grids[self._level].overlay(cropped)

        return {
            "coordinates": (abs_x, abs_y),
            "needs_zoom": True,
            "zoomed_image": next_gridded,
            "cropped_raw": cropped,
            "level": self._level,
            "cell_label": label,
        }

    def get_prompt_description(self) -> str:
        if self._level >= self.max_levels:
            return ""

        grid = self.grids[self._level]
        labels = ", ".join(grid.get_all_labels())

        if self._level == 0:
            return (
                f"The screenshot has a {grid.cols}x{grid.rows} red grid overlay. "
                f"Cells are labeled at top-left corners: {labels}. "
                f"Which cell contains the target element? "
                f"Reply with ONLY the cell label (e.g., C3)."
            )
        else:
            return (
                f"This is a zoomed view with a {grid.cols}x{grid.rows} sub-grid. "
                f"Labels: {labels}. "
                f"Which cell has the exact target? Reply ONLY the label."
            )
