"""VLM Backend — Sends gridded screenshots to any vision LLM API.

Supports:
- OpenRouter (access to every model — Claude, GPT-4o, Gemini, Llama, etc.)
- Anthropic (Claude direct)
- OpenAI (GPT-4o direct)
- Any OpenAI-compatible API
"""

import base64
import os
import re
from io import BytesIO
from typing import Optional

from PIL import Image


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buf = BytesIO()
    image.save(buf, format=format)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


class VLMBackend:
    """Sends images to a vision LLM and gets text responses."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = provider

        if provider == "openrouter":
            self.model = model or "anthropic/claude-sonnet-4"
            self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
            self.base_url = "https://openrouter.ai/api/v1"
        elif provider == "anthropic":
            self.model = model or "claude-sonnet-4-20250514"
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self.base_url = None
        elif provider == "openai":
            self.model = model or "gpt-4o"
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
            self.base_url = None
        else:
            raise ValueError(f"Unknown provider: {provider}. Use: openrouter, anthropic, openai")

        if not self.api_key:
            env_var = {
                "openrouter": "OPENROUTER_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
            }[provider]
            raise ValueError(f"No API key. Set {env_var} environment variable.")

    def ask(self, image: Image.Image, prompt: str, max_tokens: int = 512) -> str:
        """Send an image + prompt to the VLM and get a text response."""
        if self.provider == "anthropic":
            return self._ask_anthropic(image, prompt, max_tokens)
        else:
            # openrouter and openai both use OpenAI-compatible API
            return self._ask_openai_compat(image, prompt, max_tokens)

    def _ask_anthropic(self, image: Image.Image, prompt: str, max_tokens: int) -> str:
        """Call Claude API directly."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        b64 = image_to_base64(image)

        message = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return message.content[0].text

    def _ask_openai_compat(self, image: Image.Image, prompt: str, max_tokens: int) -> str:
        """Call OpenAI-compatible API (works for OpenRouter, OpenAI, etc.)."""
        import openai

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = openai.OpenAI(**client_kwargs)
        b64 = image_to_base64(image)

        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.choices[0].message.content


class GhostEyes:
    """High-level grounding: grid + VLM = find any UI element.

    Usage:
        eyes = GhostEyes(provider="openrouter", api_key="sk-or-...")
        x, y = eyes.locate(screenshot, "the Safari icon in the dock")
    """

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_zoom_levels: int = 2,
    ):
        from ghost.vision.grid import RecursiveGrid

        self.vlm = VLMBackend(provider=provider, model=model, api_key=api_key)
        self.grid = RecursiveGrid()
        self.max_zoom_levels = max_zoom_levels

    def locate(
        self, screenshot: Image.Image, target: str, verbose: bool = True
    ) -> Optional[tuple[int, int]]:
        """Find a UI element on screen. Returns (x, y) pixel coordinates.

        After each zoom, verifies the target is actually in the zoomed view.
        If not, tries neighboring cells.
        """
        self.grid.reset()
        current_image = screenshot

        for level in range(self.max_zoom_levels + 1):
            gridded = self.grid.get_gridded_image(current_image)
            grid_desc = self.grid.get_prompt_description()

            prompt = (
                f"I need to click on: {target}\n\n"
                f"{grid_desc}\n\n"
                f"Look carefully at the grid overlay on this screenshot. "
                f"Which cell contains '{target}'? "
                f"IMPORTANT: Look at the ACTUAL content of each cell, not where you think it should be. "
                f"Reply with ONLY the cell label, nothing else. Example: C3"
            )

            if verbose:
                print(f"  [Level {level}] Asking VLM: '{target}'...", end=" ", flush=True)

            response = self.vlm.ask(gridded, prompt, max_tokens=32)
            cell_label = self._extract_label(response)

            if verbose:
                print(f"→ {cell_label} (raw: '{response.strip()}')")

            if cell_label is None:
                if verbose:
                    print(f"  [!] Could not parse label from: {response}")
                return None

            result = self.grid.process_selection(cell_label, current_image)

            if not result["needs_zoom"] or level == self.max_zoom_levels:
                if verbose and result["coordinates"]:
                    print(f"  [DONE] Target at ({result['coordinates'][0]}, {result['coordinates'][1]})")
                return result["coordinates"]

            # VERIFY: is the target actually visible in the zoomed region?
            zoomed = result["cropped_raw"]
            if level < self.max_zoom_levels and self._target_visible(zoomed, target):
                current_image = zoomed
            else:
                # Target not in zoomed cell — try expanded crop (3x the cell, centered)
                if verbose:
                    print(f"  [!] Target not visible in {cell_label}, trying expanded region...")
                expanded = self._expanded_crop(screenshot, cell_label, level)
                if expanded is not None:
                    # Reset grid for expanded region and re-ask
                    self.grid._level = max(0, self.grid._level - 1)
                    if self._target_visible(expanded, target):
                        current_image = expanded
                    else:
                        current_image = zoomed  # fallback
                else:
                    current_image = zoomed

        return None

    def _target_visible(self, image: Image.Image, target: str) -> bool:
        """Quick check: is the target visible in this cropped region?"""
        try:
            prompt = (
                f"Is '{target}' visible in this image? "
                f"Reply ONLY 'YES' or 'NO'."
            )
            response = self.vlm.ask(image, prompt, max_tokens=8)
            return response.strip().upper().startswith("YES")
        except Exception:
            return True  # assume yes if check fails

    def _expanded_crop(self, screenshot: Image.Image, cell_label: str, level: int) -> Optional[Image.Image]:
        """Crop a larger region centered on the selected cell (3x the cell size)."""
        grid = self.grid.grids[min(level, len(self.grid.grids) - 1)]
        parsed = grid.parse_label(cell_label)
        if parsed is None:
            return None

        col, row = parsed
        bounds = grid.cell_bounds(col, row, screenshot.size)
        cell_w = bounds[2] - bounds[0]
        cell_h = bounds[3] - bounds[1]

        # Expand by 1.5x in each direction
        cx = (bounds[0] + bounds[2]) // 2
        cy = (bounds[1] + bounds[3]) // 2
        half_w = int(cell_w * 1.5)
        half_h = int(cell_h * 1.5)

        x1 = max(0, cx - half_w)
        y1 = max(0, cy - half_h)
        x2 = min(screenshot.width, cx + half_w)
        y2 = min(screenshot.height, cy + half_h)

        # Update offset for coordinate mapping
        self.grid._offset_x = x1
        self.grid._offset_y = y1

        return screenshot.crop((x1, y1, x2, y2))

    def decide_action(
        self, screenshot: Image.Image, task: str, history: str = ""
    ) -> dict:
        """Decide what action to take next."""
        from ghost.vision.grid import GridOverlay

        grid = GridOverlay(cols=6, rows=4, label_size=18)
        gridded = grid.overlay(screenshot)

        prompt = f"""You are Ghost, an autonomous computer agent. Look at this screenshot with a grid overlay and decide the NEXT SINGLE action to complete the task.

Task: {task}

{f"Previous actions: {history}" if history else "This is the first step."}

Available actions (pick ONE):
- OPEN_APP: open an application by name (TEXT = app name, e.g., "Safari")
- OPEN_URL: open a URL directly in a browser (TEXT = "upwork.com in Safari")
- CLOSE_APP: close an application (TEXT = app name)
- SWITCH_APP: bring an app to foreground (TEXT = app name)
- CLICK: click a UI element on screen (TARGET = describe the element precisely)
- TYPE: type text into the focused field (TEXT = exact text to type)
- HOTKEY: press key combination (TEXT = combo like "command+l", "enter", "command+t")
- SCROLL: scroll the page (TEXT = "up" or "down")
- DONE: task is complete (TEXT = summary of result)

IMPORTANT RULES:
- Use OPEN_APP / OPEN_URL instead of clicking dock icons. It's faster and more reliable.
- Use CLOSE_APP instead of clicking close buttons.
- For CLICK: describe the target element very precisely (color, position, label text).
- Only output ONE action per response.
- SCROLL when content might be below the visible area.

Reply in EXACTLY this format:
REASONING: <what you see and why this action>
ACTION: <one of the actions above>
TARGET: <for CLICK only: describe the element>
TEXT: <depends on action type, see above>"""

        response = self.vlm.ask(gridded, prompt, max_tokens=512)
        return self._parse_action(response)

    def _extract_label(self, response: str) -> Optional[str]:
        """Extract a cell label from VLM response."""
        response = response.strip()

        match = re.match(r"^([A-Z]\d{1,2})$", response)
        if match:
            return match.group(1)

        match = re.search(r"\b([A-Z]\d{1,2})\b", response)
        if match:
            return match.group(1)

        return None

    def _parse_action(self, text: str) -> dict:
        """Parse VLM output into structured action."""
        result = {"action": "UNKNOWN", "target": None, "text": None, "reasoning": text}

        r = re.search(r"REASONING:\s*(.+?)(?=\nACTION:|\Z)", text, re.DOTALL)
        a = re.search(r"ACTION:\s*([\w_]+)", text)  # support OPEN_APP, CLOSE_APP etc.
        t = re.search(r"TARGET:\s*(.+?)(?=\nTEXT:|\n(?:REMEMBER|NOTE|RULE|LOG|USER|LEARN):|\Z)", text, re.DOTALL)
        x = re.search(r"TEXT:\s*(.+?)(?=\n(?:REMEMBER|NOTE|RULE|LOG|USER|LEARN|REASONING|ACTION):|\Z)", text, re.DOTALL)

        if r: result["reasoning"] = r.group(1).strip()
        if a: result["action"] = a.group(1).strip().upper()
        if t: result["target"] = t.group(1).strip()
        if x: result["text"] = x.group(1).strip()

        return result
