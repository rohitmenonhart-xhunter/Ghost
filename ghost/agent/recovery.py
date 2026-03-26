"""Error Recovery — Structured retry logic when actions fail.

Instead of blindly retrying, Ghost follows a recovery ladder:
1. Retry same action (maybe timing issue)
2. Scroll and retry (element might be off-screen)
3. Refresh/reload and retry
4. Try alternative approach (ask AI for a different way)
5. Give up gracefully (log what failed for learning)
"""

import time
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class RecoveryAttempt:
    strategy: str
    action: str
    success: bool
    error: Optional[str] = None


class ErrorRecovery:
    """Structured error recovery with escalating strategies."""

    def __init__(
        self,
        max_retries: int = 4,
        retry_delay: float = 1.0,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._failure_counts: dict[str, int] = {}  # track repeated failures

    def attempt_recovery(
        self,
        action_fn: Callable,
        action_name: str,
        scroll_fn: Optional[Callable] = None,
        refresh_fn: Optional[Callable] = None,
        alternative_fn: Optional[Callable] = None,
    ) -> RecoveryAttempt:
        """Try to execute an action with escalating recovery strategies.

        Args:
            action_fn: The action to attempt. Returns True on success.
            action_name: Description for logging.
            scroll_fn: Function to scroll (for strategy 2).
            refresh_fn: Function to refresh/reload (for strategy 3).
            alternative_fn: Function for alternative approach (for strategy 4).
        """
        strategies = [
            ("retry", action_fn),
            ("scroll_retry", lambda: self._scroll_and_retry(action_fn, scroll_fn)),
            ("refresh_retry", lambda: self._refresh_and_retry(action_fn, refresh_fn)),
            ("alternative", alternative_fn),
        ]

        for i, (strategy_name, strategy_fn) in enumerate(strategies):
            if i >= self.max_retries:
                break
            if strategy_fn is None:
                continue

            try:
                time.sleep(self.retry_delay)
                success = strategy_fn()
                if success:
                    # Reset failure count on success
                    self._failure_counts[action_name] = 0
                    return RecoveryAttempt(
                        strategy=strategy_name,
                        action=action_name,
                        success=True,
                    )
            except Exception as e:
                continue

        # All strategies failed
        self._failure_counts[action_name] = self._failure_counts.get(action_name, 0) + 1
        return RecoveryAttempt(
            strategy="exhausted",
            action=action_name,
            success=False,
            error=f"All {self.max_retries} recovery strategies failed",
        )

    def should_give_up(self, action_name: str, threshold: int = 3) -> bool:
        """Check if Ghost should stop retrying an action entirely."""
        return self._failure_counts.get(action_name, 0) >= threshold

    def reset(self, action_name: Optional[str] = None):
        """Reset failure counts."""
        if action_name:
            self._failure_counts.pop(action_name, None)
        else:
            self._failure_counts.clear()

    def _scroll_and_retry(self, action_fn: Callable, scroll_fn: Optional[Callable]) -> bool:
        """Strategy 2: scroll to reveal hidden elements, then retry."""
        if scroll_fn:
            scroll_fn()
            time.sleep(1)
        return action_fn()

    def _refresh_and_retry(self, action_fn: Callable, refresh_fn: Optional[Callable]) -> bool:
        """Strategy 3: refresh the page/view, then retry."""
        if refresh_fn:
            refresh_fn()
            time.sleep(2)
        return action_fn()
