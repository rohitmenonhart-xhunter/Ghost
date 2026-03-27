# Silver Browser — Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        SILVER BROWSER                             │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Native UI Layer                            │ │
│  │            (SwiftUI / GTK / WPF per platform)                 │ │
│  │                                                                │ │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────────┐  │ │
│  │  │ Ghost   │ │ Spaces   │ │ Command │ │ Settings /       │  │ │
│  │  │ Panel   │ │ Manager  │ │ Palette │ │ Privacy Controls │  │ │
│  │  └────┬────┘ └────┬─────┘ └────┬────┘ └──────┬───────────┘  │ │
│  └───────┼───────────┼────────────┼──────────────┼──────────────┘ │
│          │           │            │              │                 │
│  ┌───────┼───────────┼────────────┼──────────────┼──────────────┐ │
│  │       │     Control Layer (Rust + Python)     │              │ │
│  │       │                                       │              │ │
│  │  ┌────▼──────┐ ┌──────────┐ ┌────────────┐ ┌─▼───────────┐ │ │
│  │  │ Ghost     │ │ Ad       │ │ Privacy    │ │ API Server  │ │ │
│  │  │ Agent     │ │ Shield   │ │ Guard      │ │ :7777       │ │ │
│  │  │ Engine    │ │ Engine   │ │ Engine     │ │ REST + MCP  │ │ │
│  │  └────┬──────┘ └────┬─────┘ └─────┬──────┘ └──────┬──────┘ │ │
│  └───────┼──────────────┼─────────────┼───────────────┼────────┘ │
│          │        Mojo IPC            │               │          │
│  ┌───────┼──────────────┼─────────────┼───────────────┼────────┐ │
│  │       ▼              ▼             ▼               ▼        │ │
│  │              Chromium Service Process                        │ │
│  │                                                              │ │
│  │  Blink (rendering) + V8 (JavaScript)                        │ │
│  │  + Skia Graphite (GPU rendering, 15% boost)                 │ │
│  │  + Tab Hibernation (85% memory savings)                     │ │
│  │  + Process Isolation (crash one tab, others survive)        │ │
│  │                                                              │ │
│  │  Google services: REMOVED                                    │ │
│  │  Telemetry: REMOVED                                          │ │
│  │  Safe Browsing: replaced with local lists                    │ │
│  │  Sync: replaced with local + optional E2EE sync             │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Chromium Service Process

### Base: Chromium (latest stable branch)

**What we keep:**
- Blink rendering engine
- V8 JavaScript engine
- Skia Graphite GPU rasterization
- WebGPU, WebAssembly, all modern APIs
- DevTools Protocol (CDP)
- Extension system (MV2 + MV3)
- Process-per-tab isolation
- Network stack

**What we strip (following Brave's deviations):**
- Google API keys
- Google Safe Browsing → local filter lists
- Google Sync → local storage + optional E2EE sync
- Google Translate → our AI translation
- Google Lens
- Chrome Autofill server calls
- Usage statistics reporting
- Crash reporting (unless opted in)
- Background fetch for Google services
- Chrome Signin
- Keystone updater (macOS) → our own updater
- All `*.google.com` phone-home endpoints

**What we add at engine level:**
- `adblock-rust` network filter (Brave's library)
- Cookie partitioning (per first-party context)
- Fingerprint randomization hooks
- Tab hibernation (suspend inactive tabs, restore on focus)
- DOM accessibility bridge (for Ghost agent)

### OWL Architecture (from OpenAI Atlas)

Chromium runs as an **independent service process**, not embedded in our UI.

```
Silver UI Process          Chromium Service Process
(SwiftUI/GTK/WPF)         (Blink + V8)
      │                          │
      │◄──── Mojo IPC ──────────►│
      │                          │
      │  Commands:                │  Events:
      │  → navigate(url)          │  ← page_loaded
      │  → click(element)         │  ← dom_changed
      │  → get_dom()              │  ← navigation
      │  → inject_css()           │  ← download_started
      │  → execute_js()           │  ← tab_created
```

**Why OWL:**
- Silver UI starts instantly (native code, no Chromium boot wait)
- If Chromium crashes, UI stays alive
- Engineers work on UI without building Chromium
- Chromium ships as a prebuilt binary
- Tiny upstream diff — easy to rebase on new Chromium versions

---

## Layer 2: Control Layer

### Ad Shield Engine

```
Every network request passes through:

Request → adblock-rust filter check (5.7μs) → allow / block
                                                    │
                                              ┌─────▼──────┐
                                              │ Block Stats │
                                              │ per page    │
                                              └─────────────┘
```

**Components:**
- `adblock-rust` — Brave's Rust-based filter engine
  - FlatBuffers serialization (75% memory reduction)
  - Supports: EasyList, EasyPrivacy, uBlock filters, custom lists
  - OTA filter updates (no browser update needed)
- YouTube SSAI handler
  - Parses video manifest (MPD/HLS)
  - Identifies ad segments by duration/pattern
  - Skips ad segments, plays content
  - Updated via OTA heuristic rules
- SponsorBlock integration
  - Community-sourced sponsor segment database
  - Auto-skip: sponsors, intros, outros, interaction reminders
- Cookie consent auto-handler
  - "I don't care about cookies" ruleset
  - Auto-rejects non-essential cookies
  - Auto-dismisses consent dialogs

### Privacy Guard Engine

```
Per-tab privacy state:

Normal:   standard cookies, standard fingerprint, history saved
Shield:   session cookies only, randomized fingerprint, no history
Ghost:    + proxy routing, different IP, zero local traces
```

**Components:**
- Fingerprint randomizer
  - Canvas: noise injected into readback
  - WebGL: randomized renderer/vendor strings
  - Audio: randomized AudioContext output
  - Seed: per-session, per-site (eTLD+1)
- Cookie partitioner
  - Per first-party context isolation
  - Third-party cookies partitioned (not blocked — doesn't break sites)
  - JS cookies: 7-day max lifetime
  - HTTP cookies: 6-month max lifetime
- Referrer policy
  - `strict-origin-when-cross-origin` enforced
  - Strips path on cross-origin requests
- Proxy integration (Ghost tabs)
  - Built-in SOCKS5 proxy support
  - Optional: user-provided proxy, Tor routing

### Ghost Agent Engine

```
User: Cmd+K → "apply to Upwork jobs"
                     │
                     ▼
        ┌────────────────────────┐
        │   Ghost Agent Engine   │
        │                        │
        │  1. Read DOM (CDP)     │
        │  2. Read OCR (screen)  │
        │  3. Build text context │
        │  4. Ask LLM (any model)│
        │  5. Execute action     │
        │  6. Verify result      │
        │  7. Log to memory      │
        │  8. Repeat or done     │
        └────────────────────────┘
```

**Components:**
- DOM reader (via CDP — Chrome DevTools Protocol)
  - Interactive elements with positions
  - Page text content
  - Scroll state
  - Form fields and values
- OCR engine (RapidOCR, for popups/overlays)
  - Catches elements outside the DOM
  - Google OAuth popups, file dialogs, system alerts
- LLM router
  - OpenRouter (any model)
  - Anthropic direct
  - OpenAI direct
  - Local (Ollama, LM Studio, any OpenAI-compatible)
  - WebGPU (in-browser small model for fast tasks)
- Memory system
  - SOUL.md: agent identity
  - MEMORY.md: learned facts
  - Task replay library
  - Episodic logs
- Action executor
  - Click, type, scroll via CDP
  - File dialog handler (AX tree + OCR)
  - Form filler
  - Tab manager

### API Server (localhost:7777)

```
External apps ──► localhost:7777 ──► Control Layer ──► Chromium
                    │
                    ├── REST API (/api/*)
                    ├── MCP Server (/mcp)
                    ├── WebSocket (/ws) for real-time events
                    └── CLI (silver command)
```

**Endpoints:**

```
Navigation:
  POST /api/navigate          → go to URL
  POST /api/back              → go back
  POST /api/forward           → go forward
  POST /api/reload            → reload page

Page Interaction:
  POST /api/click             → click element by ID
  POST /api/fill              → fill form field
  POST /api/type              → type text
  POST /api/scroll            → scroll page
  POST /api/select            → select dropdown option

Data:
  GET  /api/page              → get page info (title, URL, DOM elements)
  GET  /api/page/text         → get page text content
  GET  /api/page/elements     → get interactive elements
  POST /api/extract           → AI-powered data extraction
  GET  /api/screenshot        → capture current screen

Tabs:
  GET  /api/tabs              → list all tabs
  POST /api/tabs/new          → open new tab
  POST /api/tabs/close        → close tab
  POST /api/tabs/switch       → switch to tab

Spaces:
  GET  /api/spaces            → list spaces
  POST /api/spaces/new        → create space
  POST /api/spaces/switch     → switch space

AI Agent:
  POST /api/task              → run Ghost agent task
  POST /api/loop              → start a loop task
  POST /api/loop/stop         → stop a running loop
  GET  /api/memory            → get Ghost memory

Automation:
  POST /api/watch             → set up page change webhook
  POST /api/schedule          → create scheduled task
  GET  /api/schedule          → list scheduled tasks
  DELETE /api/schedule/:id    → delete scheduled task

Workflow:
  POST /api/record/start      → start recording actions
  POST /api/record/stop       → stop recording, return workflow
  POST /api/replay            → replay a recorded workflow
```

**MCP Server:**
- Implements Model Context Protocol
- Any MCP client (Claude Code, Cursor, etc.) connects automatically
- Tools exposed: navigate, click, extract, task, tabs, etc.

---

## Layer 3: Native UI

### Platform-Specific UI

| Platform | UI Framework | Why |
|----------|-------------|-----|
| macOS | SwiftUI + AppKit | Native performance, system integration |
| Linux | GTK4 + libadwaita | GNOME integration, Wayland support |
| Windows | WPF / WinUI 3 | Native Windows look and feel |

### UI Components

```
┌─────────────────────────────────────────────────────┐
│ [Space indicators: 🟢 Work  🔵 Personal  🟣 Dev]    │
├─────────────────────────────────────────────────────┤
│ [◄] [►] [↻] [🔒 https://example.com         ] [⌘K] │
├─────────────────────────────────────────────────────┤
│ Tab 1 │ Tab 2 │ Tab 3 │ [+]          [Shield: 🟢] │
├────────┬────────────────────────────────┬───────────┤
│        │                                │           │
│ Ghost  │     Web Content                │ Tools     │
│ Panel  │     (Chromium renders here)    │ Panel     │
│        │                                │           │
│ Cmd+K  │                                │ API Test  │
│ Memory │                                │ Screenshot│
│ Tasks  │                                │ Research  │
│        │                                │ PDF       │
│        │                                │           │
├────────┴────────────────────────────────┴───────────┤
│ [Ad Shield: 47 blocked] [Privacy: Normal] [0.3s]    │
└─────────────────────────────────────────────────────┘
```

### Command Palette (Cmd+K)

```
┌──────────────────────────────────────────────┐
│ ⌘K  Type a command or ask Ghost...           │
│                                              │
│  Recently used:                              │
│  ▸ Summarize this page                       │
│  ▸ Open Work space                           │
│  ▸ Close all shopping tabs                   │
│                                              │
│  Commands:                                   │
│  ▸ New tab          ▸ New space              │
│  ▸ Screenshot       ▸ Dark mode              │
│  ▸ Translate page   ▸ Research mode          │
│                                              │
│  Or ask anything:                            │
│  "find cheapest flight to NYC next weekend"  │
│  "apply to Upwork jobs while I sleep"        │
│  "compare prices for iPhone 16 Pro"          │
└──────────────────────────────────────────────┘
```

---

## Build System

### Repository Structure

```
silver/
├── browser/                    # Chromium patches + build config
│   ├── patches/                # Applied on top of upstream Chromium
│   ├── BUILD.gn                # Build configuration
│   └── chromium_version.txt    # Which Chromium version we track
│
├── core/                       # Silver's core (Rust)
│   ├── ad_shield/              # adblock-rust integration
│   ├── privacy_guard/          # fingerprint + cookie engine
│   ├── tab_manager/            # hibernation + smart groups
│   └── api_server/             # localhost:7777 REST + MCP
│
├── ghost/                      # Ghost agent (Python)
│   ├── agent/                  # browser control
│   ├── vision/                 # OCR + perception
│   ├── memory/                 # persistent memory
│   └── cli.py                  # ghost command
│
├── ui/                         # Native UI
│   ├── macos/                  # SwiftUI
│   ├── linux/                  # GTK4
│   └── windows/                # WPF
│
├── sdk/                        # Developer SDKs
│   ├── python/                 # from silver import Browser
│   ├── javascript/             # import { Silver } from 'silver'
│   └── cli/                    # silver command-line tool
│
└── docs/
    ├── FEATURES.md
    ├── ARCHITECTURE.md
    └── API.md
```

### Build Pipeline

```
1. Fetch upstream Chromium (pinned version)
2. Apply Silver patches (ad blocking, privacy, telemetry removal)
3. Build Chromium service binary
4. Build Silver core (Rust)
5. Build Ghost agent (Python, bundled with PyInstaller)
6. Build native UI (per platform)
7. Package: .dmg (macOS), .deb/.AppImage (Linux), .exe (Windows)
8. Sign + notarize (macOS: Apple Developer Program)
9. Distribute via Omaha 4 auto-updater
```

### Build Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Disk | 100GB | 500GB+ |
| RAM | 16GB | 32-64GB |
| CPU | 8 cores | 16+ cores |
| Build (local) | 3-8 hours | — |
| Build (distributed/EngFlow) | 15 minutes | — |

---

## Phased Delivery

### Phase 1: Foundation (Month 1-3)
- Fork Chromium, strip Google services
- Integrate adblock-rust (zero ads on all sites)
- Basic native UI (address bar, tabs, navigation)
- Tab hibernation
- macOS build only

### Phase 2: Intelligence (Month 3-5)
- Ghost agent sidebar (Cmd+K)
- DOM reader + LLM integration
- Smart form filling
- Page summarization
- Memory system
- YouTube ad blocking

### Phase 3: Workspace (Month 5-7)
- Spaces (isolated browsing contexts)
- Split view
- Page → desktop app
- Smart tab groups
- Session snapshots

### Phase 4: Platform (Month 7-9)
- API server (localhost:7777)
- MCP server
- Python/JS SDK
- CLI tool
- Workflow recording
- Webhooks + scheduled tasks

### Phase 5: Polish (Month 9-10)
- Privacy engine (fingerprint, cookies, per-tab levels)
- Universal dark mode
- AI translation
- PDF superpowers
- Screenshot + annotate
- Price tracker
- Auto-updater
- Linux + Windows builds

### Launch: Month 10
- macOS public beta
- Linux public beta
- Windows public beta
- Open-source release

---

## Team Requirements

| Role | Count | Responsibility |
|------|-------|---------------|
| Chromium/C++ engineer | 2 | Engine work, patches, ad blocking, privacy |
| Rust engineer | 1 | Core services, API server, performance |
| AI/Python engineer | 1 | Ghost agent, OCR, LLM integration |
| Native UI engineer | 1 | SwiftUI (macOS), GTK (Linux), WPF (Windows) |
| Infrastructure | 1 | CI/CD, builds, auto-updates, distribution |
| **Total** | **5-6** | **Minimum viable team** |

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Browser engine | Chromium (Blink + V8) | Web compatibility, performance, ecosystem |
| Ad blocking | adblock-rust (Brave) | Fastest (5.7μs), proven, open source |
| Core services | Rust | Memory safety, performance, no GC pauses |
| AI agent | Python (Ghost) | LLM ecosystem, rapid development |
| API server | Rust (Actix/Axum) | High performance, async, low memory |
| macOS UI | SwiftUI + AppKit | Native, performant, Apple integration |
| Linux UI | GTK4 + libadwaita | GNOME native, Wayland ready |
| Windows UI | WPF / WinUI 3 | Native Windows integration |
| Local AI | WebGPU + ONNX Runtime | In-browser inference, no server needed |
| Auto-update | Omaha 4 | Cross-platform, differential updates |
| Build system | GN + Ninja + EngFlow | Fast distributed builds |

---

*Architecture designed by Hitroo Labs. Open source.*
