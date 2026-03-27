<p align="center">
  <img src="assets/logo.png" alt="Ghost" width="150">
</p>

<h1 align="center">Ghost</h1>

<p align="center">
  <strong>AI browser agent that controls your computer.</strong><br>
  Type a task. Ghost does it. DOM + OCR + Memory.
</p>

<p align="center">
  <a href="https://pypi.org/project/ghostagent/"><img src="https://img.shields.io/pypi/v/ghostagent?color=red" alt="PyPI"></a>
  <a href="https://github.com/rohitmenonhart-xhunter/Ghost/stargazers"><img src="https://img.shields.io/github/stars/rohitmenonhart-xhunter/Ghost?style=social" alt="Stars"></a>
  <a href="https://github.com/rohitmenonhart-xhunter/Ghost/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License"></a>
</p>

---

## Install & Run

```bash
pip install ghostagent
export OPENROUTER_API_KEY="your-key-here"
ghost
```

```
╔══════════════════════════════════════════╗
║  👻 Ghost v0.2.0                         ║
║  AI browser agent. DOM + OCR + Memory.   ║
║  Type a task. Ghost does it.             ║
╚══════════════════════════════════════════╝

  Permissions
    ◉ Browser Control    Open, navigate, click, type in Chrome
    ◉ Screen Reading     Capture screenshots, read text via OCR
    ◉ File System        Read/write files, manage downloads
    ◉ Clipboard          Read/write system clipboard
    ◉ App Management     Open, close, switch applications
    ◉ Keyboard/Mouse     Click, type, scroll, hotkeys

  Grant all permissions? [y/n]: y
  ✓ All permissions granted.
  ✓ Ghost is ready.

  ghost> Sign into Upwork with Google using rohit@gmail.com
    Step 1: NAVIGATE upwork.com/login
    Step 2: CLICK "Continue with Google"
    Step 3: CLICK "rohit@gmail.com"
    ✓ Signed into Upwork

  ghost> Go to HackerNews and get the top 5 stories
    ✓ 1. Why so many control rooms were seafoam green
      2. Show HN: I built a search engine for RSS feeds
      3. ...

  ghost> Convert my PDF at ~/Downloads/report.pdf to DOCX
    Step 1: NAVIGATE cloudconvert.com
    Step 2: CLICK "Select File"
    [DIALOG] File picker detected → Downloads → report.pdf → Open
    Step 3: CLICK "Convert"
    Step 4: CLICK "Download"
    ✓ Saved report.docx to Downloads

  ghost> /quit
  👻 Ghost vanishes...
```

---

## What is Ghost?

Ghost is a **terminal agent** — like Claude Code but for browser tasks. You type what you want, Ghost opens Chrome and does it on your real system with your real cookies, logins, and sessions.

No sandboxed browser. No Playwright. No Selenium. Your actual Chrome.

---

## Why Ghost?

Every other browser agent sends **screenshots to a vision model** for every action. Ghost reads the **DOM as text** — 50x cheaper, faster, more accurate.

![Cost Comparison](assets/cost_comparison.png)

![Accuracy Comparison](assets/accuracy_comparison.png)

---

## How It Works

![How Ghost Works](assets/how_it_works.png)

```
Them:   Screenshot → Vision LLM ($$$) → guess pixel coordinates → click

Ghost:  Read DOM as text → LLM picks element ID → exact click
        + OCR catches popups, dialogs, overlays
        + Memory replays known tasks at zero cost
```

### Three perception layers, cheapest first

![Perception Layers](assets/perception_layers.png)

![Token Usage](assets/token_usage.png)

---

## Commands

| Command | What it does |
|---------|-------------|
| `ghost` | Start Ghost |
| `/help` | Show all commands |
| `/model [name]` | Switch LLM (e.g., `/model openai/gpt-4o`) |
| `/memory` | Show what Ghost remembers |
| `/tasks` | Show completed tasks |
| `/tabs` | List open browser tabs |
| `/screenshot` | Save current screen |
| `/quit` | Exit |
| **[anything else]** | **Ghost executes it as a task** |

---

## Use any LLM

Switch models on the fly inside Ghost:

```
ghost> /model anthropic/claude-sonnet-4-6
✓ Switched to claude-sonnet-4-6

ghost> /model openai/gpt-4.6
✓ Switched to gpt-4.6

ghost> /model google/gemini-3.1-pro
✓ Switched to gemini-3.1-pro

ghost> /model google/gemini-2.5-flash
✓ Switched to gemini-2.5-flash (cheapest)
```

Works with every model on [OpenRouter](https://openrouter.ai).

---

## What Ghost can do

**Data extraction**
```
ghost> Go to Y Combinator's top companies and get the top 10 names
```

**Form filling**
```
ghost> Go to example.com/signup and fill: name=Rohit, email=rohit@example.com
```

**Authenticated workflows** (uses your real Chrome cookies)
```
ghost> Go to my Gmail and find the latest email from Amazon
```

**File uploads & downloads**
```
ghost> Upload ~/Downloads/report.pdf to ilovepdf.com, convert to DOCX, download it
```

**Google sign-in flows**
```
ghost> Sign into Upwork with Google using rohit@gmail.com
```

**Multi-step research**
```
ghost> Search Google for "best AI agents 2026", get top 5 results, save to ~/research.txt
```

---

## Memory

Ghost remembers across sessions. Ask it something once, it never forgets.

```
ghost> /memory
┌─────────────────────────────────────────┐
│ MEMORY.md                               │
│                                         │
│ - Upwork login uses Google OAuth        │
│ - Safari icon is 5th in dock            │
│ - User prefers Claude Sonnet 4.6        │
└─────────────────────────────────────────┘
```

**Task Replay**: First time costs $0.003. Second time costs $0.000.

---

## Benchmarks

![Benchmarks](assets/benchmarks.png)

| Agent | Approach | Cost/task | Accuracy | Memory |
|-------|----------|-----------|----------|--------|
| Claude Computer Use | Screenshots → VLM | $0.10-5.00 | ~85% | No |
| OpenAI Operator | Screenshots → VLM | $0.10-5.00 | ~85% | No |
| Browser Use | Playwright + LLM | $0.01-0.05 | ~89% | No |
| **Ghost** | **DOM + OCR + text LLM** | **$0.003** | **~99%** | **Yes** |

---

## Permissions

When Ghost starts, it asks for permission to:

| Permission | Why Ghost needs it |
|-----------|-------------------|
| **Browser Control** | Navigate, click, type in Chrome via DevTools Protocol |
| **Screen Reading** | OCR for popups, dialogs, and overlays outside the DOM |
| **File System** | Read/write files, handle downloads |
| **Clipboard** | Copy/paste data between apps |
| **App Management** | Open/close/fullscreen Chrome |
| **Keyboard/Mouse** | Physical input when DOM clicks aren't enough |

Ghost runs on **your machine**. Nothing is sent to any server except LLM API calls (your chosen provider).

---

## Requirements

- Python 3.10+
- Google Chrome
- [OpenRouter API key](https://openrouter.ai) (free to start)

## Install from source

```bash
git clone https://github.com/rohitmenonhart-xhunter/Ghost.git
cd Ghost
pip install -e .
ghost
```

## License

Apache 2.0

---

Built by [Rohit Menon](https://github.com/rohitmenonhart-xhunter)
