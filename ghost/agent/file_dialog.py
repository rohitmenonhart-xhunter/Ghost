"""File Dialog Handler — Navigate native dialogs using Accessibility Tree + OCR.

When a file open/save dialog appears, Ghost CANNOT use browser DOM.
It switches to Accessibility Tree + OCR to:
1. Read the sidebar (Recents, Desktop, Documents, Downloads)
2. Click the right folder
3. Read file names in the list
4. Select the target file
5. Click Open/Save

This is the same structural perception approach used for native apps,
applied specifically to file dialogs.
"""

import os
import time
from typing import Optional

import pyautogui

from ghost.agent.screen import ScreenCapture
from ghost.vision.ocr import ScreenOCR, TextRegion
from ghost.desktop.accessibility import AccessibilityReader, UIElement


class FileDialogHandler:
    """Navigate native file dialogs using Accessibility Tree + OCR."""

    def __init__(self):
        self.screen = ScreenCapture()
        self.ocr = ScreenOCR()
        self.ax = AccessibilityReader()

    def is_file_dialog_open(self) -> bool:
        """Detect if a native file dialog is open.

        Uses OCR to look for dialog-specific text patterns.
        """
        screenshot = self.screen.capture()
        regions = self.ocr.extract(screenshot, min_confidence=0.4)

        text_combined = " ".join(r.text.lower() for r in regions)

        # File dialog indicators
        indicators = [
            "cancel",           # always has Cancel button
            "open",             # Open button (file open dialog)
            "save",             # Save button (save dialog)
            "show options",     # macOS file dialog
            "recents",          # sidebar item
            "downloads",        # sidebar item
            "favourites",       # sidebar label
            "favorites",
            "documents",        # sidebar item
            "desktop",          # sidebar item
        ]

        matches = sum(1 for ind in indicators if ind in text_combined)
        return matches >= 3

    def get_dialog_state(self) -> dict:
        """Read the full state of the file dialog via AX tree + OCR.

        Returns structured info about what's visible in the dialog.
        """
        screenshot = self.screen.capture()
        ocr_regions = self.ocr.extract(screenshot, min_confidence=0.4)
        ax_elements = self.ax.get_app_elements(max_elements=100, max_depth=12)

        # Categorize what we see
        sidebar_items = []
        file_list = []
        buttons = []
        text_fields = []
        current_folder = ""

        # From accessibility tree
        for el in ax_elements:
            role = el.role.lower()
            name = el.name.lower() if el.name else ""

            if role in ("button",) and el.clickable:
                buttons.append(el)
            elif role in ("textfield", "text_field", "searchfield", "combobox"):
                text_fields.append(el)
            elif role in ("statictext",) and el.value:
                # Could be current folder path
                if "/" in el.value or ":" in el.value:
                    current_folder = el.value
            elif role in ("cell", "row") and el.clickable:
                file_list.append(el)
            elif role in ("outline", "table"):
                pass  # container

        # From OCR — find sidebar items and file names
        sidebar_keywords = ["recents", "shared", "favourites", "favorites",
                           "applications", "desktop", "documents", "downloads",
                           "icloud", "locations"]

        for r in ocr_regions:
            text_lower = r.text.lower().strip()
            if text_lower in sidebar_keywords:
                sidebar_items.append({"text": r.text, "x": r.x, "y": r.y})

        # Find file names (items in the main list area)
        # File names are usually in the center/right area of the dialog
        for r in ocr_regions:
            if r.text.strip().endswith((".pdf", ".docx", ".txt", ".png", ".jpg",
                                        ".csv", ".xlsx", ".py", ".html", ".zip",
                                        ".md", ".json")):
                file_list.append({"text": r.text, "x": r.x, "y": r.y, "source": "ocr"})

        return {
            "sidebar": sidebar_items,
            "files": file_list,
            "buttons": buttons,
            "text_fields": text_fields,
            "current_folder": current_folder,
            "ax_elements": ax_elements,
            "ocr_regions": ocr_regions,
        }

    def navigate_to_folder(self, folder_name: str) -> bool:
        """Click a sidebar item to navigate to a folder.

        folder_name: "Downloads", "Desktop", "Documents", "Recents", etc.
        """
        state = self.get_dialog_state()
        folder_lower = folder_name.lower()

        # Try sidebar items from OCR first (more reliable text matching)
        for item in state["sidebar"]:
            if folder_lower in item["text"].lower():
                click_x = item["x"]
                click_y = item["y"]
                print(f"    [DIALOG] Clicking sidebar: {item['text']} at ({click_x},{click_y})")
                pyautogui.click(click_x, click_y)
                time.sleep(1)
                return True

        # Try accessibility tree elements
        for el in state["ax_elements"]:
            name = (el.name or "").lower()
            value = (el.value or "").lower()
            if folder_lower in name or folder_lower in value:
                if el.clickable and el.x > 0:
                    print(f"    [DIALOG] Clicking AX element: {el.name} at ({el.x},{el.y})")
                    pyautogui.click(el.x, el.y)
                    time.sleep(1)
                    return True

        # Last resort: OCR scan for the text anywhere
        screenshot = self.screen.capture()
        region = self.ocr.find_text(screenshot, folder_name)
        if region:
            print(f"    [DIALOG] Clicking OCR text: {region.text} at ({region.x},{region.y})")
            pyautogui.click(region.x, region.y)
            time.sleep(1)
            return True

        return False

    def select_file(self, filename: str, max_scrolls: int = 10) -> bool:
        """Find and click a file in the file list.

        Scrolls through the file list if file isn't immediately visible.
        Uses OCR scan → scroll → OCR scan loop.
        """
        filename_lower = filename.lower()

        for scroll_attempt in range(max_scrolls + 1):
            time.sleep(0.5)
            screenshot = self.screen.capture()
            regions = self.ocr.extract(screenshot, min_confidence=0.3)

            # Search OCR text for the filename — strict matching
            # Extract the core name without extension for matching
            name_no_ext = filename_lower.rsplit(".", 1)[0]  # "hq26-4ocvf2 - hitroo"
            ext = filename_lower.rsplit(".", 1)[-1] if "." in filename_lower else ""

            # Build unique keywords from the filename (skip generic words)
            skip_words = {"pdf", "docx", "txt", "png", "jpg", "jpeg", "csv", "xlsx", "zip", "the", "a", "an"}
            name_keywords = set(
                w for w in name_no_ext.replace("-", " ").replace("_", " ").replace(".", " ").split()
                if len(w) >= 3 and w not in skip_words
            )

            best_match = None
            best_score = 0

            for r in regions:
                text_lower = r.text.lower().strip()

                # Skip very short OCR text (single words like "PDF", "Open")
                if len(text_lower) < 5:
                    continue

                # Score: how many unique name keywords appear in this OCR text?
                text_words = set(text_lower.replace("-", " ").replace("_", " ").replace(".", " ").split())
                matched_keywords = name_keywords & text_words
                score = len(matched_keywords)

                # Bonus: if the OCR text contains most of the filename
                if name_no_ext[:10] in text_lower:
                    score += 5

                # Must match at least 1 unique keyword (not just extension)
                if score > best_score and score >= 1:
                    best_match = r
                    best_score = score

            if best_match:
                # macOS file list rows are taller than the text inside them.
                # OCR gives us the text bbox, but we need to click the ROW center.
                #
                # Strategy: find the next text region below this one.
                # The row center = midpoint between this text's y and next text's y.
                # If no text below, use y2 + half the typical row height (~20px).
                click_x = best_match.x

                # Find the next OCR region below this one in the file list
                regions_below = sorted(
                    [r for r in regions if r.y > best_match.y + 5 and abs(r.x - best_match.x) < 200],
                    key=lambda r: r.y,
                )

                if regions_below:
                    next_y = regions_below[0].y1  # top of next text
                    click_y = (best_match.y + next_y) // 2  # midpoint = row center
                else:
                    click_y = best_match.y2 + 10  # offset below text bottom

                print(f"    [DIALOG] Found file: \"{best_match.text}\" text_y={best_match.y} click_y={click_y}")
                pyautogui.click(click_x, click_y)
                time.sleep(0.3)
                return True

            # Also check accessibility tree
            ax_elements = self.ax.get_app_elements(max_elements=100, max_depth=12)
            for el in ax_elements:
                name = (el.name or "").lower()
                if filename_lower in name and el.x > 0:
                    # AX elements also need slight downward offset in list views
                    click_y = el.y + (el.height // 4) if el.height > 10 else el.y
                    print(f"    [DIALOG] Found AX file: {el.name} at ({el.x},{click_y})")
                    pyautogui.click(el.x, click_y)
                    time.sleep(0.3)
                    return True

            # Not found yet — scroll down in the file list
            if scroll_attempt < max_scrolls:
                print(f"    [DIALOG] File not visible, scrolling... ({scroll_attempt + 1}/{max_scrolls})")

                # Find the file list area by locating dialog landmarks:
                # - Sidebar is on the left (~first 20% of dialog width)
                # - File list is in the middle (~30-60% of dialog width)
                # - Buttons (Cancel/Open) are at the bottom
                #
                # macOS file dialog layout:
                # ┌──────────┬──────────────────┬──────────┐
                # │ Sidebar  │   File List       │ Preview  │
                # │          │   ← SCROLL HERE   │          │
                # ├──────────┴──────────────────┴──────────┤
                # │ [Show Options]      [Cancel]  [Open]   │
                # └────────────────────────────────────────┘

                # Estimate file list center based on dialog position
                # Find "Cancel" or "Open" button to know dialog bottom
                dialog_bottom = screenshot.size[1] * 0.7  # default 70% down
                dialog_left = screenshot.size[0] * 0.2    # past the sidebar

                for r in regions:
                    if r.text.lower().strip() in ("cancel", "open"):
                        dialog_bottom = r.y1 - 30  # above the buttons
                        break

                # Find sidebar right edge (look for sidebar items)
                for r in regions:
                    if r.text.lower().strip() in ("downloads", "documents", "desktop", "favourites", "recents"):
                        dialog_left = max(dialog_left, r.x2 + 40)  # right of sidebar text
                        break

                # File list center: between sidebar right edge and 70% of screen width
                file_list_x = int((dialog_left + screenshot.size[0] * 0.6) / 2)
                file_list_y = int(dialog_bottom / 2 + 50)

                print(f"    [DIALOG] Moving to file list area ({file_list_x},{file_list_y}) to scroll")
                pyautogui.moveTo(file_list_x, file_list_y, duration=0.2)
                time.sleep(0.2)
                pyautogui.scroll(-3)  # scroll down
                time.sleep(0.5)

        print(f"    [DIALOG] Could not find \"{filename}\" after {max_scrolls} scroll attempts")
        return False

    def click_button(self, button_text: str) -> bool:
        """Click a button in the dialog (Open, Save, Cancel, etc.)."""
        screenshot = self.screen.capture()
        regions = self.ocr.extract(screenshot, min_confidence=0.4)
        button_lower = button_text.lower()

        for r in regions:
            if r.text.lower().strip() == button_lower:
                # With correct coordinate mapping (no downscaling), bbox center is accurate
                print(f"    [DIALOG] Clicking button: {r.text} at ({r.x},{r.y})")
                pyautogui.click(r.x, r.y)
                time.sleep(1)
                return True

        # Try AX tree for buttons
        ax_elements = self.ax.get_app_elements(max_elements=100, max_depth=12)
        for el in ax_elements:
            if el.clickable and button_lower in (el.name or "").lower():
                click_y = el.y + (el.height // 4) if el.height > 10 else el.y
                print(f"    [DIALOG] Clicking AX button: {el.name} at ({el.x},{click_y})")
                pyautogui.click(el.x, click_y)
                time.sleep(1)
                return True

        return False

    def select_file_full(self, filepath: str) -> bool:
        """Full flow: navigate to folder + select file + click Open.

        filepath: full path like /Users/rohit/Downloads/HITROO.pdf
        """
        parts = filepath.rsplit("/", 1)
        folder = parts[0] if len(parts) > 1 else ""
        filename = parts[1] if len(parts) > 1 else filepath

        # Map folder to sidebar name
        folder_lower = folder.lower()
        if "downloads" in folder_lower:
            sidebar_name = "Downloads"
        elif "desktop" in folder_lower:
            sidebar_name = "Desktop"
        elif "documents" in folder_lower:
            sidebar_name = "Documents"
        else:
            sidebar_name = os.path.basename(folder)

        # Step 1: Navigate to the right folder
        print(f"    [DIALOG] Navigating to {sidebar_name}...")
        if self.navigate_to_folder(sidebar_name):
            time.sleep(1)
        else:
            print(f"    [DIALOG] Could not find {sidebar_name} in sidebar")

        # Step 2: Find and select the file
        print(f"    [DIALOG] Looking for {filename}...")
        if self.select_file(filename):
            time.sleep(0.5)

            # Step 3: Click Open
            print(f"    [DIALOG] Clicking Open...")
            self.click_button("Open")
            return True
        else:
            print(f"    [DIALOG] Could not find file: {filename}")
            # Try double-clicking in case it just needs selection confirmation
            return False

    def format_for_llm(self) -> str:
        """Get dialog state formatted for AI decision making."""
        state = self.get_dialog_state()

        parts = ["FILE DIALOG OPEN:"]

        if state["current_folder"]:
            parts.append(f"  Current folder: {state['current_folder']}")

        if state["sidebar"]:
            parts.append("  Sidebar: " + ", ".join(s["text"] for s in state["sidebar"]))

        if state["files"]:
            parts.append("  Files visible:")
            for f in state["files"][:15]:
                text = f.get("text", "") if isinstance(f, dict) else f.name
                parts.append(f"    - {text}")

        if state["buttons"]:
            parts.append("  Buttons: " + ", ".join(b.name for b in state["buttons"] if b.name))

        return "\n".join(parts)
