"""Ghost — AI browser agent that costs 50x less.

DOM + OCR + Memory. Works with any LLM.

Usage:
    from ghost import Ghost

    ghost = Ghost()
    result = ghost.browse("Go to Hacker News and get the top 5 stories")
    print(result)
"""

__version__ = "0.3.0"

from ghost.core.ghost import Ghost

__all__ = ["Ghost"]
