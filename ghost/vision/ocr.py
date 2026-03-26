"""Screen OCR — Extract all text with bounding boxes from screenshots.

Returns every piece of visible text with its exact pixel position.
Combined with DOM data, gives the AI complete screen awareness.

Backends (in order of preference):
  1. RapidOCR — Best accuracy, uses PaddleOCR models via ONNX, cross-platform
  2. Apple Vision — Fast on macOS, decent quality
  3. Tesseract — Fallback, works everywhere
"""

import platform
from dataclasses import dataclass
from typing import Optional

from PIL import Image

SYSTEM = platform.system()


@dataclass
class TextRegion:
    """A piece of text found on screen with its bounding box."""
    text: str
    x: int          # center x
    y: int          # center y
    x1: int         # left
    y1: int         # top
    x2: int         # right
    y2: int         # bottom
    confidence: float  # 0.0 to 1.0


class ScreenOCR:
    """Extract text + bounding boxes from screenshots."""

    def __init__(self, backend: Optional[str] = None):
        if backend:
            self.backend = backend
        else:
            # Auto-detect best available backend
            try:
                from rapidocr_onnxruntime import RapidOCR
                self.backend = "rapid"
                self._rapid = RapidOCR()
            except ImportError:
                if SYSTEM == "Darwin":
                    self.backend = "vision"
                else:
                    self.backend = "tesseract"

    def extract(self, image: Image.Image, min_confidence: float = 0.5) -> list[TextRegion]:
        """Extract all text regions from a screenshot."""
        if self.backend == "rapid":
            return self._extract_rapid(image, min_confidence)
        elif self.backend == "vision":
            return self._extract_vision(image, min_confidence)
        elif self.backend == "tesseract":
            return self._extract_tesseract(image, min_confidence)
        else:
            raise ValueError(f"Unknown OCR backend: {self.backend}")

    def _extract_rapid(self, image: Image.Image, min_confidence: float) -> list[TextRegion]:
        """Use RapidOCR (PaddleOCR models via ONNX). Best accuracy."""
        import numpy as np

        img_array = np.array(image)
        result, _ = self._rapid(img_array)

        if not result:
            return []

        regions = []
        for box, text, conf in result:
            conf_val = float(conf) if isinstance(conf, (int, float)) else float(str(conf))
            if conf_val < min_confidence:
                continue

            # box is 4 corner points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            x1 = int(min(p[0] for p in box))
            y1 = int(min(p[1] for p in box))
            x2 = int(max(p[0] for p in box))
            y2 = int(max(p[1] for p in box))

            regions.append(TextRegion(
                text=text.strip(),
                x=(x1 + x2) // 2,
                y=(y1 + y2) // 2,
                x1=x1, y1=y1, x2=x2, y2=y2,
                confidence=conf_val,
            ))

        return regions

    def _extract_vision(self, image: Image.Image, min_confidence: float) -> list[TextRegion]:
        """Use Apple Vision framework for OCR. Fast, runs on Neural Engine."""
        import Quartz
        import objc

        # Convert PIL image to CGImage
        import io
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        data = buf.getvalue()

        ns_data = Quartz.CFDataCreate(None, data, len(data))
        source = Quartz.CGImageSourceCreateWithData(ns_data, None)
        cg_image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)

        if cg_image is None:
            return self._extract_tesseract(image, min_confidence)

        # Use VNRecognizeTextRequest via objc
        VNImageRequestHandler = objc.lookUpClass("VNImageRequestHandler")
        VNRecognizeTextRequest = objc.lookUpClass("VNRecognizeTextRequest")

        handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
        request = VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(1)  # 1 = accurate
        request.setUsesLanguageCorrection_(True)

        success = handler.performRequests_error_([request], None)
        if not success:
            return self._extract_tesseract(image, min_confidence)

        results = []
        img_w, img_h = image.size

        observations = request.results() or []
        for observation in observations:
            # Get the top candidate
            candidates = observation.topCandidates_(1)
            if not candidates:
                continue

            candidate = candidates[0]
            text = str(candidate.string())
            confidence = float(candidate.confidence())

            if confidence < min_confidence:
                continue

            # Bounding box: normalized, bottom-left origin
            bbox = observation.boundingBox()
            bx = float(bbox.origin.x)
            by = float(bbox.origin.y)
            bw = float(bbox.size.width)
            bh = float(bbox.size.height)

            # Convert to pixel coords, flip Y
            x1 = int(bx * img_w)
            y1 = int((1.0 - by - bh) * img_h)
            x2 = int((bx + bw) * img_w)
            y2 = int((1.0 - by) * img_h)

            results.append(TextRegion(
                text=text, x=(x1 + x2) // 2, y=(y1 + y2) // 2,
                x1=x1, y1=y1, x2=x2, y2=y2,
                confidence=confidence,
            ))

        return results

    def _extract_tesseract(self, image: Image.Image, min_confidence: float) -> list[TextRegion]:
        """Use Tesseract OCR. Works on Linux/Windows."""
        import subprocess
        import json
        import tempfile
        import os

        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp, format="PNG")
            tmp_path = tmp.name

        try:
            # Run tesseract with TSV output for bounding boxes
            result = subprocess.run(
                ["tesseract", tmp_path, "stdout", "--psm", "3", "tsv"],
                capture_output=True, text=True, timeout=30,
            )

            regions = []
            for line in result.stdout.strip().split("\n")[1:]:  # skip header
                parts = line.split("\t")
                if len(parts) < 12:
                    continue

                conf = float(parts[10]) / 100.0 if parts[10] != "-1" else 0
                text = parts[11].strip()

                if not text or conf < min_confidence:
                    continue

                x1 = int(parts[6])
                y1 = int(parts[7])
                w = int(parts[8])
                h = int(parts[9])
                x2 = x1 + w
                y2 = y1 + h

                regions.append(TextRegion(
                    text=text,
                    x=(x1 + x2) // 2,
                    y=(y1 + y2) // 2,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=conf,
                ))

            return regions

        finally:
            os.unlink(tmp_path)

    def find_text(self, image: Image.Image, query: str, min_confidence: float = 0.5) -> Optional[TextRegion]:
        """Find a specific text on screen. Returns the best matching region."""
        regions = self.extract(image, min_confidence)
        query_lower = query.lower()

        # Exact match first
        for r in regions:
            if query_lower == r.text.lower():
                return r

        # Contains match
        for r in regions:
            if query_lower in r.text.lower():
                return r

        # Fuzzy: find the region whose text is most similar
        best = None
        best_score = 0
        for r in regions:
            score = self._similarity(query_lower, r.text.lower())
            if score > best_score and score > 0.5:
                best = r
                best_score = score

        return best

    def format_for_llm(self, regions: list[TextRegion], max_regions: int = 50) -> str:
        """Format OCR results as compact text for the LLM.

        Groups nearby text into logical lines to reduce noise.
        """
        if not regions:
            return "No text detected on screen."

        # Sort by vertical position (top to bottom), then horizontal
        sorted_regions = sorted(regions, key=lambda r: (r.y1, r.x1))

        # Group into lines (regions within 10px vertically = same line)
        lines = []
        current_line = []
        current_y = -999

        for r in sorted_regions[:max_regions]:
            if abs(r.y - current_y) > 15:
                if current_line:
                    lines.append(current_line)
                current_line = [r]
                current_y = r.y
            else:
                current_line.append(r)

        if current_line:
            lines.append(current_line)

        # Format each line
        output = []
        for line in lines:
            line.sort(key=lambda r: r.x1)
            text = " ".join(r.text for r in line)
            y_pos = line[0].y
            x_range = f"x:{line[0].x1}-{line[-1].x2}"
            output.append(f"  [{y_pos:4d}px] {text}")

        return "\n".join(output)

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Simple word overlap similarity."""
        a_words = set(a.split())
        b_words = set(b.split())
        if not a_words or not b_words:
            return 0
        return len(a_words & b_words) / max(len(a_words), len(b_words))
