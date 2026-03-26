"""Cross-platform screen capture."""

import platform
from io import BytesIO
from typing import Optional

from PIL import Image


class ScreenCapture:
    """Fast cross-platform screenshot capture using mss."""

    def __init__(self, max_resolution: Optional[tuple[int, int]] = None):
        # Don't downscale — OCR coordinates must match screen coordinates exactly.
        # Downscaling causes click offset bugs.
        self.max_resolution = max_resolution or (3840, 2160)
        self._backend = self._detect_backend()

    def _detect_backend(self) -> str:
        system = platform.system()
        if system == "Linux":
            return "mss"
        elif system == "Darwin":
            return "mss"
        elif system == "Windows":
            return "mss"
        return "mss"

    def capture(self, monitor: int = 0) -> Image.Image:
        """Capture the screen and return as PIL Image."""
        import mss

        with mss.mss() as sct:
            # monitor 0 = all monitors, 1 = primary, 2+ = others
            target = sct.monitors[monitor + 1] if monitor < len(sct.monitors) - 1 else sct.monitors[1]
            raw = sct.grab(target)
            image = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        # Store original size (needed for coordinate mapping)
        self._last_capture_size = image.size

        # Downscale for model input if needed, but track the scale
        if image.width > self.max_resolution[0] or image.height > self.max_resolution[1]:
            self._model_scale = min(
                self.max_resolution[0] / image.width,
                self.max_resolution[1] / image.height,
            )
            image.thumbnail(self.max_resolution, Image.Resampling.LANCZOS)
        else:
            self._model_scale = 1.0

        return image

    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Capture a specific region of the screen."""
        import mss

        region = {"left": x, "top": y, "width": width, "height": height}
        with mss.mss() as sct:
            raw = sct.grab(region)
            return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    @property
    def screen_size(self) -> tuple[int, int]:
        """Get primary screen resolution."""
        import mss

        with mss.mss() as sct:
            monitor = sct.monitors[1]  # primary
            return (monitor["width"], monitor["height"])

    @property
    def scale_factor(self) -> float:
        """Get HiDPI scale factor."""
        actual = self.screen_size
        screenshot = self.capture()
        if actual[0] > 0:
            return screenshot.width / actual[0]
        return 1.0
