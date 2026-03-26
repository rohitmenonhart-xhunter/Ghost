"""Browser Agent — AI + DOM = cheap, accurate, fast.

The AI sees a TEXT list of elements (not screenshots).
It picks which element to interact with. DOM handles the rest.
Tokens per action: ~100-200 (vs ~3000 with screenshots).
"""

import os
import re
import time
from typing import Optional

from ghost.browser.cdp import BrowserController


class BrowserAgent:
    """AI-powered browser control using DOM elements."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        port: int = 9222,
    ):
        self.browser = BrowserController(port=port)

        # Set up LLM (text-only, no vision needed for DOM mode)
        self.provider = provider
        self.model = model or "anthropic/claude-sonnet-4"
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")

        if not self.api_key:
            raise ValueError("Set OPENROUTER_API_KEY environment variable.")

    def _ask_llm(self, prompt: str, max_tokens: int = 512) -> str:
        """Send a text-only prompt to the LLM. No images = cheap."""
        import openai

        client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1" if self.provider == "openrouter" else None,
        )

        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def ensure_connected(self):
        """Make sure browser is running and connected."""
        if not self.browser.is_available():
            self.browser.launch_with_debugging()
            time.sleep(2)

        try:
            self.browser.get_current_url()
        except Exception:
            self.browser.connect(0)

    def run(self, task: str, max_steps: int = 20) -> str:
        """Execute a browser task using AI + DOM."""
        self.ensure_connected()

        history = []
        final_result = ""

        print(f"\n{'='*60}")
        print(f"  GHOST BROWSER — {task}")
        print(f"{'='*60}\n")

        dialog_attempts = 0
        max_dialog_attempts = 3

        for step in range(1, max_steps + 1):
            # 0. Check if a native file dialog is open (max 3 attempts)
            if dialog_attempts < max_dialog_attempts:
                if self._check_and_handle_file_dialog(task, history):
                    dialog_attempts += 1
                    history.append(f"Handled file dialog (attempt {dialog_attempts})")
                    time.sleep(2)
                    continue
            else:
                # Exhausted dialog attempts — press Escape to dismiss and move on
                import pyautogui
                pyautogui.press("escape")
                time.sleep(1)
                dialog_attempts = 0
                history.append("Dismissed stuck file dialog")

            # 1. Read current state
            try:
                url = self.browser.get_current_url()
                title = self.browser.get_page_title()
                elements = self.browser.get_interactive_elements()
                element_list = self.browser.format_elements_for_vlm(elements)
                page_text = self.browser.get_page_text()[:2000]
            except Exception:
                # DOM might be unavailable (dialog open, page loading, etc.)
                # Fall back to OCR + accessibility
                url = "unknown"
                title = "unknown"
                elements = []
                element_list = "DOM unavailable — page may be loading or a dialog is open"
                page_text = ""

            # 2. Ask AI what to do next
            history_str = "\n".join(f"  Step {i+1}: {h}" for i, h in enumerate(history[-8:]))

            prompt = f"""You are Ghost, a browser automation agent. Complete the user's task by interacting with the webpage.

TASK: {task}

CURRENT STATE:
  URL: {url}
  Title: {title}

INTERACTIVE ELEMENTS:
{element_list}

PAGE TEXT (first 2000 chars):
{page_text[:1000]}

{"HISTORY:" + chr(10) + history_str if history else "This is the first step."}

AVAILABLE ACTIONS (pick ONE):
  CLICK [id]              — click element by ID number
  FILL [id] [text]        — type text into an input field
  NAVIGATE [url]          — go to a URL
  SCROLL [up/down]        — scroll the page
  PRESS [key]             — press a key (enter, tab, escape)
  READ                    — read more page content (for gathering info)
  UPLOAD [filepath]       — upload a file (handles the native file dialog automatically)
  DONE [result]           — task complete, provide the result

RULES:
  - Pick the SIMPLEST action that makes progress
  - For file uploads: first CLICK the upload/choose-file button, then use UPLOAD [filepath]
  - For sign-in flows: click the right button, fill fields, press enter
  - When gathering info: use READ to get page content, then DONE with the answer
  - If stuck after 3 tries on the same element, try a different approach

Reply in this format:
REASONING: <brief explanation>
ACTION: <one action from above>"""

            print(f"  Step {step}: ", end="", flush=True)
            response = self._ask_llm(prompt, max_tokens=300)

            # 3. Parse the action
            action = self._parse_action(response)
            reasoning = action.get("reasoning", "")
            act = action.get("action", "")

            print(f"{act}")
            if reasoning:
                short = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                print(f"    → {short}")

            # 4. Execute
            try:
                result = self._execute_action(act, elements)
                history.append(f"{act} → {result}")

                if act.startswith("DONE"):
                    final_result = act[5:].strip() if len(act) > 5 else result
                    print(f"\n  Task complete.")
                    break

            except Exception as e:
                print(f"    [ERROR] {e}")
                history.append(f"{act} → ERROR: {e}")

            time.sleep(1)

        print(f"\n{'='*60}")
        if final_result:
            print(f"  RESULT:\n{final_result}")
        print(f"{'='*60}\n")

        return final_result

    def _parse_action(self, response: str) -> dict:
        """Parse LLM response into action."""
        result = {"reasoning": "", "action": ""}

        r = re.search(r"REASONING:\s*(.+?)(?=\nACTION:|\Z)", response, re.DOTALL)
        a = re.search(r"ACTION:\s*(.+?)(?=\n[A-Z]+:|\Z)", response, re.DOTALL)

        if r:
            result["reasoning"] = r.group(1).strip()
        if a:
            result["action"] = a.group(1).strip()

        # Fallback: if no ACTION: tag, try to find action in response
        if not result["action"]:
            for line in response.strip().split("\n"):
                line = line.strip()
                if line.startswith(("CLICK", "FILL", "NAVIGATE", "SCROLL", "PRESS", "READ", "DONE")):
                    result["action"] = line
                    break

        return result

    def _execute_action(self, action: str, elements: list[dict]) -> str:
        """Execute a parsed action."""
        if not action:
            return "No action"

        parts = action.split(None, 2)
        cmd = parts[0].upper()

        if cmd == "CLICK" and len(parts) >= 2:
            eid = self._parse_id(parts[1])
            el = self._find_element(eid, elements)
            if el:
                # Always use coordinate click — works for cross-origin iframes,
                # OAuth buttons, and everything else. More reliable than JS click.
                self.browser.click_at(el["x"], el["y"])
                time.sleep(2)

                # Check if a new window/tab opened (OAuth popups etc.)
                self._handle_new_windows()

                return f"Clicked '{el.get('text', eid)}'"
            else:
                return f"Element {eid} not found"

        elif cmd == "FILL" and len(parts) >= 3:
            eid = self._parse_id(parts[1])
            text = parts[2].strip().strip("'\"")
            el = self._find_element(eid, elements)
            if el:
                # Click the field first, then type
                self.browser.click_at(el["x"], el["y"])
                time.sleep(0.3)
                # Clear existing text
                self.browser._cdp.send("Runtime.evaluate", {
                    "expression": "document.activeElement.value = ''"
                })
                self.browser.type_text(text)
                time.sleep(0.5)
                return f"Filled '{text}' into element {eid}"
            else:
                return f"Element {eid} not found"

        elif cmd == "NAVIGATE" and len(parts) >= 2:
            url = parts[1].strip()
            self.browser.navigate(url)
            time.sleep(2)
            return f"Navigated to {url}"

        elif cmd == "SCROLL":
            direction = parts[1].lower() if len(parts) >= 2 else "down"
            self.browser.scroll(direction)
            time.sleep(1)
            return f"Scrolled {direction}"

        elif cmd == "PRESS" and len(parts) >= 2:
            key = parts[1].strip().lower()
            self.browser.press_key(key)
            time.sleep(1)
            return f"Pressed {key}"

        elif cmd == "READ":
            text = self.browser.get_page_text()[:3000]
            return text

        elif cmd == "UPLOAD" and len(parts) >= 2:
            filepath = parts[1].strip().strip("'\"")
            return self._handle_upload(filepath)

        elif cmd == "DONE":
            result = action[5:].strip() if len(action) > 5 else "Task complete"
            return result

        else:
            return f"Unknown action: {action}"

    def _handle_upload(self, filepath: str) -> str:
        """Handle file upload via native file dialog."""
        from ghost.agent.file_dialog import FileDialogHandler
        handler = FileDialogHandler()

        # Wait for file dialog to appear
        time.sleep(2)

        if handler.is_file_dialog_open():
            print(f"    [UPLOAD] File dialog detected, selecting: {filepath}")
            handler.select_file(filepath)
            time.sleep(2)
            return f"Uploaded file: {filepath}"
        else:
            # Dialog might not be open yet — the CLICK on upload button should trigger it
            # Try typing path anyway
            print(f"    [UPLOAD] No dialog detected, trying path input")
            handler.select_file(filepath)
            time.sleep(2)
            return f"Attempted upload: {filepath}"

    def _check_and_handle_file_dialog(self, task: str, history: list) -> bool:
        """Auto-detect native file dialogs and handle them via AX tree + OCR.

        When a file dialog appears:
        1. DOM goes dead (browser page is blocked)
        2. Ghost detects the dialog via OCR patterns
        3. Switches to Accessibility Tree + OCR to navigate the dialog
        4. Finds the right folder, selects the right file, clicks Open
        5. Returns to DOM mode when dialog closes
        """
        from ghost.agent.file_dialog import FileDialogHandler
        handler = FileDialogHandler()

        if not handler.is_file_dialog_open():
            return False

        print(f"    [DIALOG] Native file dialog detected! Switching to AX+OCR mode.")

        # Show what the dialog looks like
        dialog_info = handler.format_for_llm()
        print(f"    {dialog_info[:200]}")

        # Try to extract file path from task description
        import re
        path_match = re.search(r"(/[\w/.\-\s]+\.\w+)", task)
        if path_match:
            filepath = path_match.group(1).strip()
            print(f"    [DIALOG] Found path in task: {filepath}")
            success = handler.select_file_full(filepath)
            if success:
                return True

        # No path in task — ask AI what to do with dialog context
        prompt = f"""A native file dialog is open on screen.

Task: {task}

Dialog state:
{dialog_info}

Recent actions: {', '.join(history[-3:])}

What file should be selected? Reply with the FULL file path (e.g., /Users/rohit/Downloads/file.pdf)"""

        filepath = self._ask_llm(prompt, max_tokens=150).strip().strip("'\"")

        # Clean up AI response — extract just the path
        path_match = re.search(r"(/[\w/.\-\s]+\.\w+)", filepath)
        if path_match:
            filepath = path_match.group(1).strip()
            print(f"    [DIALOG] AI chose: {filepath}")
            success = handler.select_file_full(filepath)
            return success

        return False

    def _handle_new_windows(self):
        """If a new tab/popup opened (e.g., Google OAuth), switch to it."""
        time.sleep(1)
        tabs = self.browser.list_tabs()
        page_tabs = [t for t in tabs if t.get("type") == "page"]

        if len(page_tabs) > 1:
            # Find the newest tab (likely the popup)
            # Connect to the last page tab
            newest = page_tabs[-1]
            ws_url = newest.get("webSocketDebuggerUrl")
            if ws_url:
                print(f"    [POPUP] Switching to: {newest.get('title', '?')[:50]}")
                self.browser.disconnect()
                from ghost.browser.cdp import CDPConnection
                self.browser._cdp = CDPConnection(ws_url)
                time.sleep(1)

    def _parse_id(self, s: str) -> int:
        """Extract element ID from string like '5' or '[5]'."""
        m = re.search(r"\d+", s)
        return int(m.group()) if m else 0

    def _find_element(self, eid: int, elements: list[dict]) -> Optional[dict]:
        """Find element by ID."""
        for el in elements:
            if el.get("id") == eid:
                return el
        return None
