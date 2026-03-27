"""Ghost Config — Persistent settings stored at ~/.ghost/config.json.

Stores:
- API key (so users don't need env vars)
- Model preference
- Provider
"""

import json
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".ghost"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "api_key": "",
    "provider": "openrouter",
    "model": "anthropic/claude-sonnet-4",
}


def load_config() -> dict:
    """Load config from disk, or return defaults."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            # Merge with defaults for any missing keys
            return {**DEFAULTS, **data}
        except Exception:
            return dict(DEFAULTS)
    return dict(DEFAULTS)


def save_config(config: dict):
    """Save config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key() -> str:
    """Get API key from config or environment."""
    import os
    # Config file takes priority, then env var
    config = load_config()
    key = config.get("api_key", "")
    if key:
        return key
    return os.environ.get("OPENROUTER_API_KEY", "")


def set_api_key(key: str):
    """Save API key to config."""
    config = load_config()
    config["api_key"] = key
    save_config(config)


def get_model() -> str:
    """Get current model."""
    return load_config().get("model", DEFAULTS["model"])


def set_model(model: str):
    """Save model preference."""
    config = load_config()
    config["model"] = model
    save_config(config)
