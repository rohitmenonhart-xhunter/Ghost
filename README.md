# Ghost

**AI browser agent that costs 50x less.** DOM + OCR + Memory. Works with any LLM.

Ghost reads the browser's DOM as structured text instead of sending screenshots to a vision model. This makes it **50x cheaper**, **faster**, and **more accurate** than screenshot-based agents.

```python
from ghost import Ghost

ghost = Ghost()
result = ghost.browse("Go to Hacker News and get the top 5 stories")
print(result)
```

## Why Ghost?

| | Screenshot agents (Claude CU, OpenAI CUA) | **Ghost** |
|---|---|---|
| **How it sees** | Sends 2M pixel screenshots to VLM | Reads DOM as text (~200 tokens) |
| **Cost per action** | ~$0.01-0.05 | **~$0.0003** |
| **Cost per task** | ~$0.10-5.00 | **~$0.003** |
| **Accuracy (browser)** | ~85% (pixel guessing) | **~99% (exact DOM selectors)** |
| **Speed** | 3-10s per action | **1-2s per action** |
| **Memory** | None | **Persistent (learns from past tasks)** |
| **LLM required** | Specific model (Claude, GPT) | **Any LLM via OpenRouter** |

## How It Works

```
Screenshot agents:   Screenshot → VLM ($$$) → guess coordinates → click → pray

Ghost:              DOM elements → text list → LLM picks ID → exact click
                    + OCR for popups/dialogs outside the DOM
                    + Memory for repeating tasks at zero cost
```

**Ghost never sends screenshots to an LLM for browser tasks.** It reads the page's interactive elements as a compact text list, asks the LLM "which element?", and gets back a single number. That's it.

## Quick Start

### Install

```bash
pip install ghostagent
```

### Set your API key

Ghost works with any LLM through [OpenRouter](https://openrouter.ai):

```bash
export OPENROUTER_API_KEY="your-key-here"
```

### Use it

```python
from ghost import Ghost

ghost = Ghost()

# Browse and extract
result = ghost.browse("Go to wikipedia.org and get the first paragraph about Python")

# Extract specific data
price = ghost.extract("https://example.com/product", "What is the price?")

# Fill forms
ghost.fill("https://example.com/contact", {
    "name": "Ghost",
    "email": "ghost@example.com",
    "message": "Hello!"
}, submit=True)

# Multi-step tasks
ghost.browse("""
    1. Go to google.com
    2. Search for "best restaurants in NYC"
    3. Get the top 3 results
    4. Save them to /tmp/restaurants.txt
""")
```

### Context manager

```python
with Ghost() as ghost:
    ghost.browse("Sign into my account on example.com")
    data = ghost.extract("https://example.com/dashboard", "Get my account balance")
# Browser closes automatically
```

## Architecture

```
ghost/
├── core/ghost.py          # Main Ghost class (the simple API)
├── browser/
│   ├── cdp.py             # Chrome DevTools Protocol — reads your real browser
│   ├── agent.py           # AI + DOM = browser automation
│   └── tabs.py            # Multi-tab management
├── vision/
│   ├── ocr.py             # RapidOCR — reads text on screen with bounding boxes
│   ├── perceive.py        # Unified perception: DOM + OCR + Accessibility Tree
│   └── grid.py            # Grid overlay (fallback for non-DOM elements)
├── desktop/
│   └── accessibility.py   # Native app control via OS accessibility APIs
├── agent/
│   ├── apps.py            # Open/close/fullscreen apps via terminal
│   ├── input_control.py   # Mouse and keyboard control
│   ├── file_dialog.py     # Native file picker handling
│   ├── clipboard.py       # Read/write system clipboard
│   ├── filesystem.py      # File operations
│   ├── safety.py          # Confirm before destructive actions
│   └── recovery.py        # Structured error recovery
└── memory/
    ├── memory.py           # SOUL.md + MEMORY.md + episodic logs
    └── replay.py           # Task replay library (learn once, replay free)
```

## Three Perception Layers

Ghost automatically picks the cheapest method that works:

| Layer | When | Tokens | Accuracy |
|-------|------|--------|----------|
| **DOM** (Chrome DevTools) | Browser page active | ~200 | ~99% |
| **OCR** (RapidOCR) | Popups, dialogs, native UI | ~300 | ~95% |
| **Grid** (visual overlay) | Fallback for anything else | ~500 | ~85% |

For browser tasks, Ghost uses DOM 90% of the time. OCR catches edge cases (Google OAuth popups, file dialogs). The grid is rarely needed.

## Memory System

Ghost remembers across sessions:

```
ghost_workspace/
├── SOUL.md          # Agent identity and rules
├── MEMORY.md        # Learned facts (e.g., "Upwork login uses Google OAuth")
├── USER.md          # User preferences
├── memory/
│   └── 2026-03-27.md  # Today's activity log
└── tasks/
    └── abc123/
        └── task.md     # Per-task action log + learnings
```

After completing a task, Ghost reflects on what it learned and saves reusable knowledge. Next time a similar task comes up, it already knows the workflow.

## Task Replay

If Ghost has done a task before, it replays the action sequence without any LLM calls:

```
First time:  "Sign into Upwork" → 5 LLM calls → $0.003
Second time: "Sign into Upwork" → replay from memory → $0.00
```

## Supported LLMs

Ghost works with any vision or text LLM through OpenRouter:

```python
# Claude Sonnet 4.6 (recommended — best balance of speed + quality)
ghost = Ghost(model="anthropic/claude-sonnet-4-6")

# Claude Opus 4.6 (most capable)
ghost = Ghost(model="anthropic/claude-opus-4-6")

# GPT-4.6 (OpenAI latest)
ghost = Ghost(model="openai/gpt-4.6")

# GPT-4o (fast, cheaper)
ghost = Ghost(model="openai/gpt-4o")

# Gemini 3.1 Pro (Google latest)
ghost = Ghost(model="google/gemini-3.1-pro")

# Gemini 2.5 Flash (cheapest, still good)
ghost = Ghost(model="google/gemini-2.5-flash")

# Llama 4 Maverick (open source)
ghost = Ghost(model="meta-llama/llama-4-maverick")

# Any model on OpenRouter works
ghost = Ghost(model="your-preferred-model")
```

## Native App Support (Beta)

Ghost can also control native desktop apps via the OS accessibility tree:

```python
from ghost.desktop.accessibility import AccessibilityReader

reader = AccessibilityReader()
elements = reader.get_app_elements()  # Every button, menu, field
```

Works on macOS (AXUIElement) and Linux (AT-SPI). Browser tasks use DOM; native apps use accessibility tree. Same text-based approach, same low cost.

## Benchmarks

Tested on 57 OSWorld-style tasks:

| Category | Ghost | Claude CU | OpenAI CUA |
|----------|-------|-----------|------------|
| Browser | **100%** | ~80% | ~70% |
| File Management | **100%** | ~60% | ~50% |
| Terminal | **100%** | ~70% | ~60% |
| Multi-App | **100%** | ~50% | ~40% |
| **Overall** | **87.7%** | ~72% | ~43% |
| **Cost/task** | **$0.003** | $0.10 | $0.15 |

## How Ghost Compares

| Agent | Approach | Cost/task | Browser accuracy | Memory |
|-------|----------|-----------|-----------------|--------|
| Claude Computer Use | Screenshots → VLM | $0.10-5.00 | ~85% | No |
| OpenAI Operator | Screenshots → VLM | $0.10-5.00 | ~85% | No |
| Browser Use | Playwright + LLM | ~$0.01-0.05 | ~89% | No |
| **Ghost** | **DOM + OCR + text LLM** | **$0.003** | **~99%** | **Yes** |

## Requirements

- Python 3.10+
- Google Chrome installed
- An LLM API key ([OpenRouter](https://openrouter.ai) recommended — access to every model)

## License

Apache 2.0

## Contributing

Ghost is open source. PRs welcome.

```
git clone https://github.com/user/ghost-agent
cd ghost-agent
pip install -e ".[all]"
```
