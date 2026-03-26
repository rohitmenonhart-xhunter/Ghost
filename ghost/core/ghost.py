"""Ghost — The main developer-facing class.

Simple, clean API. Everything complex is hidden inside.

Usage:
    # Basic
    ghost = Ghost()
    result = ghost.browse("Go to Hacker News and get the top 5 stories")

    # With options
    ghost = Ghost(model="anthropic/claude-sonnet-4", headless=False)
    result = ghost.browse("Sign into my Upwork account", max_steps=20)

    # Extract data
    data = ghost.extract("https://news.ycombinator.com", "Get all story titles and their points")

    # Fill forms
    ghost.fill("https://example.com/form", {"name": "Rohit", "email": "rohit@example.com"})

    # Multi-step task
    ghost.browse('''
        1. Go to google.com
        2. Search for "Ghost AI agent"
        3. Save the first 3 result titles to /tmp/results.txt
    ''')
"""

import os
import time
from typing import Optional


class Ghost:
    """AI browser agent. DOM + OCR + Memory. Works with any LLM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-sonnet-4",
        provider: str = "openrouter",
        headless: bool = False,
        memory: bool = True,
        verbose: bool = True,
    ):
        """Initialize Ghost.

        Args:
            api_key: OpenRouter/Anthropic/OpenAI API key.
                     Defaults to OPENROUTER_API_KEY env var.
            model: LLM model to use. Any OpenRouter model works.
            provider: "openrouter", "anthropic", or "openai".
            headless: Run browser without visible window.
            memory: Enable persistent memory (SOUL.md, replay library).
            verbose: Print step-by-step progress.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model
        self.provider = provider
        self.headless = headless
        self.verbose = verbose
        self._memory_enabled = memory

        if not self.api_key:
            env_map = {
                "openrouter": "OPENROUTER_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
            }
            env_var = env_map.get(provider, "OPENROUTER_API_KEY")
            raise ValueError(
                f"No API key provided. Either pass api_key= or set {env_var} environment variable."
            )

        self._browser = None
        self._agent = None
        self._memory = None

    def _ensure_browser(self):
        """Lazy-init browser and agent on first use."""
        if self._agent is not None:
            return

        from ghost.browser.cdp import BrowserController
        from ghost.browser.agent import BrowserAgent
        from ghost.agent.apps import AppController

        self._browser = BrowserController()
        if not self._browser.is_available():
            self._browser.launch_with_debugging()
            time.sleep(3)

        # Fullscreen for better OCR
        apps = AppController()
        apps.switch_to_app("Google Chrome", fullscreen=True)
        time.sleep(1)

        self._agent = BrowserAgent(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
        )

        if self._memory_enabled:
            from ghost.memory.memory import GhostMemory
            self._memory = GhostMemory()

    # ── Main API ─────────────────────────────────────────────────

    def browse(self, task: str, max_steps: int = 20) -> str:
        """Execute a browser task and return the result.

        Args:
            task: Natural language description of what to do.
            max_steps: Maximum number of actions to take.

        Returns:
            Result string from the agent.

        Example:
            result = ghost.browse("Go to wikipedia.org and get the featured article title")
            print(result)
        """
        self._ensure_browser()

        # Log to memory
        if self._memory:
            self._memory.log(f"Task: {task}")

        # Check replay library for cached result
        if self._memory:
            from ghost.memory.replay import TaskReplayLibrary
            replay = TaskReplayLibrary()
            cached = replay.get_replay(task)
            if cached:
                if self.verbose:
                    print(f"  [REPLAY] Found cached task with {len(cached)} steps")
                # TODO: execute cached steps

        result = self._agent.run(task, max_steps=max_steps)

        # Log result
        if self._memory:
            self._memory.log(f"Result: {result[:100]}")

        return result

    def extract(self, url: str, query: str) -> str:
        """Navigate to a URL and extract specific information.

        Args:
            url: Website to visit.
            query: What data to extract.

        Returns:
            Extracted data as string.

        Example:
            price = ghost.extract("https://example.com/product", "What is the price?")
        """
        task = f"Navigate to {url} and extract this information: {query}. Return ONLY the extracted data."
        return self.browse(task, max_steps=10)

    def fill(self, url: str, fields: dict, submit: bool = False) -> str:
        """Navigate to a URL and fill in form fields.

        Args:
            url: Form page URL.
            fields: Dict of {field_name: value} to fill.
            submit: Whether to submit the form after filling.

        Returns:
            Result string.

        Example:
            ghost.fill("https://example.com/contact", {
                "name": "Ghost Agent",
                "email": "ghost@example.com",
                "message": "Hello from Ghost!"
            }, submit=True)
        """
        field_desc = ", ".join(f'{k}: "{v}"' for k, v in fields.items())
        task = f"Go to {url} and fill in these form fields: {field_desc}."
        if submit:
            task += " Then submit the form."
        return self.browse(task, max_steps=15)

    def click(self, url: str, target: str) -> str:
        """Navigate to a URL and click a specific element.

        Args:
            url: Page URL.
            target: Description of what to click.

        Returns:
            Result string.

        Example:
            ghost.click("https://example.com", "the Sign Up button")
        """
        return self.browse(f"Go to {url} and click on {target}", max_steps=10)

    def screenshot(self, save_path: str = "/tmp/ghost_screenshot.png") -> str:
        """Take a screenshot of the current browser state.

        Returns:
            Path to saved screenshot.
        """
        from ghost.agent.screen import ScreenCapture
        sc = ScreenCapture()
        img = sc.capture()
        img.save(save_path)
        return save_path

    def tabs(self) -> list[dict]:
        """List all open browser tabs.

        Returns:
            List of {title, url} dicts.
        """
        self._ensure_browser()
        from ghost.browser.tabs import TabManager
        tm = TabManager(self._browser)
        return tm.list_tabs()

    def close(self):
        """Close the browser and clean up."""
        if self._browser:
            from ghost.agent.apps import AppController
            AppController().close_app("Google Chrome")
            self._browser = None
            self._agent = None

    # ── Context Manager ──────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self):
        return f"Ghost(model='{self.model}', provider='{self.provider}')"
