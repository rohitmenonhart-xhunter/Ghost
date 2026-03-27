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

## Get Started

```bash
pip install ghostagent
ghost
```

Ghost walks you through setup on first run — enter your API key once, grant permissions, and you're ready.

```
╔══════════════════════════════════════════╗
║  👻 Ghost v0.3.0                         ║
║  AI browser agent. DOM + OCR + Memory.   ║
╚══════════════════════════════════════════╝

  First-time Setup
  Enter your OpenRouter API key: sk-or-v1-xxxxx
  ✓ API key saved. You won't need to enter this again.

  Grant all permissions? [y/n]: y
  ✓ Ghost is ready.
  Model: anthropic/claude-sonnet-4

  ghost> _
```

---

## What is Ghost?

Ghost is a **terminal agent** that controls your browser. Type what you want in plain English, Ghost opens Chrome and does it — on your real system, with your real cookies, logins, and sessions.

```
ghost> Sign into Upwork with Google using rohit@gmail.com
  Step 1: NAVIGATE upwork.com/login
  Step 2: CLICK "Continue with Google"
  Step 3: CLICK "rohit@gmail.com"
  ╭──── ✓ Done ────╮
  │ Signed in.      │
  ╰─────────────────╯

ghost> Get the top 5 trending repos on GitHub with star counts
  ╭──── ✓ Done ────────────────────────────────────────╮
  │ • bytedance/deer-flow — 49,092 ⭐                   │
  │ • ruvnet/RuView — 43,386 ⭐                         │
  │ • agentscope-ai/agentscope — 20,727 ⭐              │
  │ • virattt/dexter — 19,147 ⭐                        │
  │ • Yeachan-Heo/oh-my-claudecode — 13,001 ⭐          │
  ╰─────────────────────────────────────────────────────╯

ghost> Convert ~/Downloads/report.pdf to DOCX using an online converter
  Step 1: NAVIGATE cloudconvert.com
  Step 2: CLICK "Select File"
  [DIALOG] File picker → Downloads → report.pdf → Open
  Step 3: CLICK "Convert"
  Step 4: CLICK "Download"
  ╭──── ✓ Done ──────────────────────╮
  │ Saved report.docx to Downloads.   │
  ╰───────────────────────────────────╯
```

---

## Why Ghost?

Every other browser agent sends **screenshots to a vision model** for every action. Ghost reads the **DOM as text** — same information, 50x cheaper.

![Cost Comparison](assets/cost_comparison.png)

![Accuracy Comparison](assets/accuracy_comparison.png)

---

## How It Works

![How Ghost Works](assets/how_it_works.png)

Ghost uses three perception layers — cheapest first:

![Perception Layers](assets/perception_layers.png)

DOM handles 90% of actions. VLM is the last resort, not the first.

![Token Usage](assets/token_usage.png)

---

## Commands

| Command | What it does |
|---------|-------------|
| `ghost` | Start Ghost |
| `/help` | Show all commands |
| `/loop [task]` | Repeat a task continuously, Ctrl+C to stop and get summary |
| `/model [name]` | Switch LLM model (saved across sessions) |
| `/config` | View/edit API key and settings |
| `/memory` | Show what Ghost remembers |
| `/tasks` | Show completed tasks |
| `/tabs` | List open browser tabs |
| `/screenshot` | Save current screen |
| `/quit` | Exit |
| **[anything else]** | **Ghost executes it** |

---

## Loop Mode

Run a task continuously until you stop it. Ghost summarizes everything when done.

```
ghost> /loop Search Upwork for Python jobs and apply to matching ones

  🔄 Loop Mode — Press Ctrl+C to stop

  ── Iteration 1 ──
  ✓ Applied to "Django REST API developer" ($50-80/hr)

  ── Iteration 2 ──
  ✓ Applied to "FastAPI microservice project" ($40-60/hr)

  ^C

  ╭──── 🔄 Loop Summary ─────────────────────╮
  │ • Applied to 2 jobs in 3 minutes          │
  │ • Django REST API ($50-80/hr)             │
  │ • FastAPI microservice ($40-60/hr)        │
  ╰───────────────────────────────────────────╯
  Summary saved to ~/ghost_loop_summary_20260327.md
```

---

## Use Any LLM

Switch models on the fly — saved across sessions:

```
ghost> /model anthropic/claude-sonnet-4-6
✓ Switched to claude-sonnet-4-6 (saved)

ghost> /model openai/gpt-4o
✓ Switched to gpt-4o (saved)

ghost> /model google/gemini-2.5-flash
✓ Switched to gemini-2.5-flash (saved)
```

Works with every model on [OpenRouter](https://openrouter.ai) — Claude, GPT, Gemini, Llama, and more.

---

## Settings

Ghost saves everything to `~/.ghost/config.json`. Edit anytime:

```
ghost> /config
  API Key     sk-or-v1...fc283
  Model       anthropic/claude-sonnet-4
  Config      ~/.ghost/config.json

ghost> /config key sk-or-v1-new-key-here
✓ API key updated

ghost> /config model openai/gpt-4.6
✓ Model updated
```

---

## Memory

Ghost remembers across sessions. No other browser agent does this.

```
ghost> /memory
┌─────────────────────────────────────────┐
│ MEMORY.md                               │
│                                         │
│ - Upwork login uses Google OAuth        │
│ - User prefers Claude Sonnet            │
│ - GitHub trending is at /trending       │
└─────────────────────────────────────────┘
```

**Task Replay**: First run costs $0.003. Repeat runs cost $0.000.

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

## Fresh Mac Setup

```bash
# 1. Install Ghost
pip install ghostagent

# 2. Run it (first time walks you through setup)
ghost

# 3. Grant Accessibility permission (one-time)
#    System Settings → Privacy & Security → Accessibility
#    Add your terminal app → Toggle ON
```

That's it. Ghost auto-syncs your Chrome profile on first launch.

---

## Architecture

```
ghost/
├── cli.py                 # Terminal agent (the ghost command)
├── config.py              # Persistent settings (~/.ghost/config.json)
├── browser/
│   ├── cdp.py             # Chrome DevTools — reads your real browser
│   ├── agent.py           # AI + DOM automation
│   └── tabs.py            # Multi-tab management
├── vision/
│   ├── ocr.py             # RapidOCR — popups, dialogs, overlays
│   ├── perceive.py        # DOM + OCR + VLM fusion
│   └── vlm.py             # Vision LLM (fallback only)
├── agent/
│   ├── apps.py            # Open/close/fullscreen apps
│   ├── file_dialog.py     # Native file picker via OCR
│   ├── clipboard.py       # Copy/paste
│   ├── safety.py          # Confirm destructive actions
│   └── recovery.py        # Error recovery
└── memory/
    ├── memory.py           # SOUL.md + episodic logs
    └── replay.py           # Task replay library
```

---

## Install from Source

```bash
git clone https://github.com/rohitmenonhart-xhunter/Ghost.git
cd Ghost
pip install -e .
ghost
```

## License

Apache 2.0

## Contributing

PRs welcome. Ghost is open source.

---

Built by [Rohit Menon](https://github.com/rohitmenonhart-xhunter)
