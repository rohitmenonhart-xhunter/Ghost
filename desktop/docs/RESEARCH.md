# AI-Native Browser: Complete Technical Research (March 2026)

## Table of Contents
1. [Browser Engines](#1-browser-engines)
2. [Ad Blocking Architecture](#2-ad-blocking-architecture)
3. [Performance — Beating Chrome](#3-performance--beating-chrome)
4. [AI Integration at Browser Level](#4-ai-integration-at-browser-level)
5. [Privacy Architecture](#5-privacy-architecture)
6. [Building & Distributing a Browser](#6-building--distributing-a-browser)
7. [Existing AI Browsers to Study](#7-existing-ai-browsers-to-study)
8. [Strategic Recommendations](#8-strategic-recommendations)

---

## 1. Browser Engines

### Chromium (Blink + V8) — The Dominant Choice

**Who uses it:** Chrome, Brave, Edge, Opera, Vivaldi, Arc, Dia, Comet, Atlas, BrowserOS, Fellou, Sigma

**Pros:**
- Fastest JavaScript/rendering performance on benchmarks (Speedometer 3.1, MotionMark)
- Largest web compatibility — sites are built for Chromium first
- WebGPU, WebAssembly, all modern APIs land here first
- Massive ecosystem: extensions, DevTools, documentation
- Proven path: Brave, Arc, and now OpenAI Atlas all fork it successfully
- Skia Graphite (new GPU rasterization backend) gives 15% boost on MotionMark

**Cons:**
- ~50GB source code, 500GB+ disk for full build
- Full build takes 3-8 hours depending on hardware (15 min with distributed builds)
- Google services deeply embedded — must strip them out
- Multi-process model is memory-hungry by design
- Chromium rebases every 3 weeks — constant maintenance burden
- Missing from raw Chromium: Widevine DRM, cloud sync, auto-updates

**How to fork:**
1. `fetch chromium` to get source (~50GB)
2. `gn gen out/Default` to configure
3. `autoninja -C out/Default chrome` to build
4. Key: DON'T do a traditional Git fork. Instead, maintain patches applied programmatically on top of upstream (like Brave does)
5. Brave uses dual-repo: `brave-browser` (orchestration) + `brave-core` (implementation)
6. OpenAI Atlas uses OWL architecture: runs Chromium as a separate service process, communicates via Mojo IPC, builds the UI in SwiftUI/AppKit — engineers never need to build Chromium locally (ships as prebuilt binary)

### Servo (Rust) — Not Ready Yet

**Status (March 2026):** Version 0.0.5. Targeting Summer 2026 Alpha on Linux/macOS.

**Pros:**
- Written in Rust — memory safety, no use-after-free bugs
- Parallel layout engine (multi-threaded by design)
- Embeddable — designed as a component, not a monolith
- Backed by Linux Foundation Europe
- Leading in Web Cryptography (ML-KEM, ML-DSA support)
- 90% of official web platform tests pass (as of Oct 2025)

**Cons:**
- NOT production-ready — tons of broken website rendering
- Performance nowhere near Blink/Gecko/WebKit yet
- 8 paid engineers + community contributors — tiny team
- No DRM support, many APIs missing
- "Far from a daily driver" — their own assessment
- Beta 2027, stable 2028

**Verdict:** Watch closely but don't build on it today. Could be interesting for an embedded use case (rendering panels inside your AI UI) but not for a full browser.

### WebKit (Safari)

**Who uses it:** Safari, GNOME Web, WPE (embedded), PlayStation, Kindle, Nintendo

**Pros:**
- Best battery efficiency and Apple hardware optimization
- Safari 26 bringing WebGPU to iOS
- Embeddable via WebKitGTK (Linux) and WPE (embedded devices)
- Strong security track record

**Cons:**
- Apple controls it — slower to adopt new web standards
- Much smaller ecosystem than Chromium
- On iOS, ALL browsers must use WebKit (though DMA may change this in EU)
- Not practical for a desktop browser competing with Chrome

### Gecko (Firefox)

**Who uses it:** Firefox, Tor Browser, Zen Browser, Mullvad Browser, LibreWolf

**Pros:**
- Best privacy engine (Enhanced Tracking Protection, Total Cookie Protection)
- Still supports Manifest V2 — full uBlock Origin works
- GeckoView available for Android embedding
- Anti-fingerprinting is more robust than Brave's approach (fixed values > randomization)
- Strong standards compliance

**Cons:**
- Firefox at <2.5% market share — declining ecosystem
- Embedding on desktop is poorly documented, no CEF equivalent
- Performance lags Blink on benchmarks
- Much harder to fork than Chromium (less modular)
- Small and shrinking team at Mozilla

### Ladybird — The Wild Card

**Status:** From-scratch engine in C++ (transitioning to Rust). 8 paid full-time engineers. Funded by Cloudflare, Shopify, FUTO, 37signals.

- 217 improvements/month, 43+ contributors
- 90% of web platform tests pass
- reCAPTCHA and HTTP/3 now work
- Alpha Summer 2026 (Linux/macOS), Beta 2027, Stable 2028
- No code borrowed from any other engine

**Verdict:** Impressive ambition but years away from being usable for production. Not viable for 2026.

### What Electron Uses

Electron embeds Chromium directly (Blink + V8) along with Node.js. It uses Chromium's content API directly (not CEF). Electron is a full app framework, not just a browser component.

### What Arc Uses/Used

Arc was Chromium-based (Blink + V8) with custom UI written entirely in Swift using native macOS technologies. Now sunset — replaced by Dia (also Chromium, also Swift, acquired by Atlassian for $610M).

### Which Engine is FASTEST?

**Benchmarks (Speedometer 3.1, 2025-2026):**
1. **Blink (Chrome/Edge)** — Fastest on Windows/Linux, especially with Skia Graphite
2. **WebKit (Safari)** — Fastest on Apple Silicon with Metal GPU, best battery life
3. **Gecko (Firefox)** — Consistently 10-20% behind Blink on Speedometer

On powerful hardware, Chromium-based browsers dominate. On Apple Silicon, Safari is competitive. But "fastest" depends on workload — Blink wins JS-heavy, WebKit wins GPU compositing on Mac.

---

## 2. Ad Blocking Architecture

### How Brave Does It — The Gold Standard

**Brave Shields** uses `adblock-rust`, an open-source Rust library:

- **Performance:** 5.7 microseconds average request classification (69x faster than previous engine)
- **Memory:** FlatBuffers-based storage — zero-copy binary format, 45MB savings across all platforms, 75% memory reduction from previous version
- **Filter syntax:** ABP filter syntax + uBlock Origin-compatible scriptlet injection
- **Two blocking types:**
  1. **Network blocking** — intercepts requests before they're made
  2. **Cosmetic filtering** — hides elements after page load, injects scriptlets to modify script behavior

**Key: It runs in the browser process, not as an extension.** This means:
- No Manifest V3 limitations
- Direct access to network stack
- Can block before requests leave the browser
- Works identically on mobile and desktop
- Uses fewer resources than any extension

**The library is open-source:** https://github.com/brave/adblock-rust — you can use it directly.

### How to Block YouTube Ads

This is the hardest ad-blocking problem in 2026:

**The YouTube SSAI Challenge:**
- YouTube started Server-Side Ad Insertion (SSAI) in March 2025
- Ads are stitched directly into the video stream on Google's servers
- The ad comes from the same domain/server as video content
- Traditional network blocking cannot distinguish ad segments from video segments

**What Still Works (March 2026):**
1. **Firefox + uBlock Origin** — MV2 still supported, full filtering power
2. **Brave Aggressive Shields** — engine-level blocking catches most pre-roll/mid-roll
3. **AdGuard system-level** — blocks 95-99% of YouTube ads including SSAI
4. **SponsorBlock** — community-maintained segment skip (different approach)

**For a custom browser, the approach would be:**
1. Use `adblock-rust` at the network layer for standard ad domains
2. Implement YouTube-specific heuristics:
   - Detect ad segments in video manifests (MPD/M3U8 parsing)
   - Skip ad segments by manipulating the media player timeline
   - Intercept and modify YouTube's ad delivery JavaScript
3. Maintain a rapid-update filter list (YouTube changes anti-adblock weekly)
4. Consider a "community intelligence" model where detection rules update OTA

### uBlock Origin Approach vs Built-in

| Aspect | uBlock Origin (Extension) | Built-in (Brave-style) |
|--------|--------------------------|----------------------|
| Manifest V3 | Crippled on Chrome (30K rule limit) | Not affected |
| Performance | Extension overhead, IPC | Native speed, no overhead |
| Mobile | Not available on Chrome mobile | Works everywhere |
| Filter lists | User-configurable, 300K+ rules | Same lists, no rule limit |
| Cosmetic filtering | Full dynamic filtering | Can be deeper (pre-render) |
| Updates | Extension store review | Ship with browser updates |

### DNS-Level vs Content Blocking

**DNS blocking (Pi-hole, AdGuard Home):**
- Blocks entire domains network-wide (all devices)
- Cannot block same-domain ads (YouTube, Facebook)
- Cannot do cosmetic filtering (element hiding)
- Cannot block HTTPS-inspected content

**Content blocking (in-browser):**
- Can inspect and modify page content
- Can block specific URLs/paths, not just domains
- Can hide elements, inject scripts
- Can handle same-domain ad serving
- Only protects the browser, not other apps

**Best approach: Both.** Browser-level content blocking for web ads + optional DNS blocking for network-wide protection.

### Manifest V3 — Why Extensions Are Crippled

**Timeline:**
- March 2025: MV2 disabled by default in Chrome
- July 2025 (Chrome 138): MV2 completely removed

**Technical limitations of MV3:**
- `declarativeNetRequest` API limited to 30,000 static rules (uBlock Origin needs 80,000-300,000)
- Dynamic rules limited to 30,000 (previously unlimited via `webRequest`)
- No synchronous request interception — only declarative, pre-registered rules
- Cosmetic filtering severely restricted
- Service workers replace persistent background pages (can be killed by browser)

**This is a Chrome/Chromium problem.** Firefox explicitly supports both MV2 and MV3. A custom Chromium fork can re-enable MV2 or bypass these limits entirely by building blocking into the browser process.

### Building Ad Blocking into the Rendering Engine

The key insight: if you control the browser, you can block at multiple levels:

1. **DNS resolution** — block known ad domains before TCP connection
2. **Network stack** — intercept requests in the browser's network service (before TLS)
3. **Resource loading** — prevent ad resources from entering the renderer
4. **DOM construction** — strip ad elements during HTML parsing
5. **Rendering/paint** — hide ad elements with zero layout cost
6. **Script execution** — intercept and neutralize ad scripts

Brave does levels 2-3 primarily. A more aggressive approach could integrate at all 6 levels, which would be a significant differentiator. Level 4 (DOM-level stripping) is particularly powerful because the ad elements never exist in the DOM tree, saving memory and preventing anti-adblock detection scripts from finding their containers.

---

## 3. Performance — Beating Chrome

### What Makes Chrome Slow

**Architecture overhead:**
- Every tab runs in a separate process (Site Isolation) — security-first, memory-expensive
- Every extension spawns separate contexts
- Speculative resource loading for pages you might visit
- Frequent garbage collection pauses script execution

**Google services bloat:**
- Google Cloud Messaging, Firebase, Push client channel updates
- Network time tracker, Domain service reliability
- Google accounts integration (GAIA)
- Chrome Privacy Sandbox APIs (Topics, Attribution Reporting)
- SafeBrowsing checks, Certificate Transparency auditing
- Telemetry: metrics reporting, crash log uploading, WebRTC debug logs

**Memory consumption:**
- Each tab: 50-300MB+ depending on content
- Each extension: 20-100MB+
- Renderer process, GPU process, network process, utility processes
- V8 heap per tab, Blink layout trees, composited layers

### What Brave Strips Out (The Template)

From the official Brave deviations wiki, here's what they remove/disable:

**Google services removed:**
- GAIA (Google accounts integration)
- Google Cloud Messaging / Firebase Cloud Messaging
- Chrome sync infrastructure
- Google URL tracker
- Popular Sites / Top Sites
- Inline extensions
- Network time tracker
- OEM default settings retrieval

**Telemetry disabled:**
- Metrics reporting
- Crash log uploading
- WebRTC debug log uploading
- Profile reset settings uploading
- SCT auditing
- Reporting Observers (enabled but no-op)

**Privacy Sandbox killed:**
- FLoC, Topics API, Trust Tokens, Web Environment Integrity
- All Chrome Privacy Sandbox APIs

**APIs disabled/modified:**
- Battery API (returns fixed values)
- Idle Detection, NFC, Web Serial (off by default)
- WebBluetooth, Digital Goods API
- Network Information API
- Cookies capped: JS-set = 7 days max, HTTP-set = 6 months max

**Network privacy:**
- SafeBrowsing proxied through Brave servers (Google never sees your IP)
- Referrer capped to strict-origin-when-cross-origin
- Secure DNS never disabled by group policy

### Memory Management Techniques

**Tab suspension/hibernation:**
- Chrome Memory Saver: 3 levels (Moderate, Balanced, Maximum)
- Sleeping tabs save 85% memory and 99% CPU (Microsoft's measurement)
- Vivaldi: hibernates after 5 minutes of inactivity
- Key: preserve form state, audio/video playback, downloads — don't suspend active tabs
- Implement a smart policy: ML-based prediction of which tabs will be revisited

**Process model optimization:**
- Share renderer processes for same-site tabs (reduce process count)
- Lazy process creation — don't spawn GPU process until needed
- Aggressive memory reclamation on tab switch
- Use PartitionAlloc (Chrome's custom allocator) — 20% memory reduction on 64-bit

**GPU acceleration:**
- Skia Graphite: new GPU rasterization backend, 15% improvement on MotionMark
- Uses Vulkan (Linux/Windows/Android), Metal (macOS/iOS), Dawn (WebGPU)
- Multi-threaded rendering by default
- Hardware-accelerated video decode (saves CPU + battery)

### Concrete Performance Wins for a Custom Browser

1. **Strip Google services** — saves 50-100MB baseline + eliminates background network
2. **Built-in ad blocking** — blocks 30-50% of network requests, major page load speedup
3. **Aggressive tab hibernation** — 85% memory savings per inactive tab
4. **No extension sandbox overhead** — AI features are native, not extension processes
5. **Prebuilt Chromium binary** (Atlas approach) — instant startup, async engine boot
6. **Predictive preloading** — AI predicts next navigation, preloads in background

---

## 4. AI Integration at Browser Level

### Architecture: Where AI Hooks In

There are two proven architectures for deep AI integration:

#### Architecture A: BrowserOS Model (Extension + Sidecar)

```
[Agent UI Extension] <--messaging--> [Controller Extension] <--HTTP--> [Bun Server]
                                            |                              |
                                     chrome.tabs API               LLM API calls
                                     chrome.windows API            Memory system
                                     chrome.bookmarks API          MCP tools
                                            |                              |
                                     [Chromium Process] <---CDP---> [CDP Server :9100]
                                            |
                                     [Go Sidecar :9000] --> MCP tools for external AI
```

**How it works:**
- Agent runs as a force-pinned extension (cannot be disabled)
- Controller extension bridges to Bun TypeScript server
- DOM access via Chrome DevTools Protocol (`Runtime.evaluate`, `Page` commands)
- Network state via CDP (no custom proxy needed)
- MCP server exposes 53+ browser tools to external AI clients
- Three modes: Chat, Agent (multi-step automation), Graph (visual workflows)

**Pros:** Minimal Chromium patches, fast iteration, hot-swappable sidecar
**Cons:** Extension messaging overhead, CDP indirection

#### Architecture B: OpenAI Atlas/OWL Model (Process Separation)

```
[Atlas App (SwiftUI/AppKit)] <---Mojo IPC---> [Chromium Process (OWL Host)]
         |                                              |
    AI Sidebar                                    Blink + V8
    Agent Mode                                    GPU rendering
    Browser Memories                              Tab management
    Custom UI                                     Network stack
```

**How it works:**
- Chromium runs as an independent service process (OWL Host)
- Atlas UI is pure SwiftUI/AppKit — one language, one stack
- Communication via Mojo (Chromium's native IPC)
- Chromium boots asynchronously — UI appears instantly
- If Chromium hangs or crashes, Atlas stays up
- Engineers never build Chromium locally — ships as prebuilt binary
- Very small diff against upstream Chromium (easy to maintain)

**Pros:** Clean separation, instant startup, crash isolation, small upstream diff
**Cons:** macOS-only (SwiftUI), requires deep Mojo expertise

### DOM Access Layer

For AI to interact with web pages, you need deep DOM access:

1. **CDP (Chrome DevTools Protocol)** — standard, well-documented
   - `Runtime.evaluate` — execute JS in page context
   - `DOM.getDocument` — get full DOM tree
   - `Page.captureScreenshot` — visual understanding
   - `Network.getResponseBody` — read network responses
   - `Input.dispatchMouseEvent` / `Input.dispatchKeyEvent` — simulate user input

2. **Direct content script injection** — via `chrome.tabs.executeScript()`
   - Can read and modify DOM directly
   - Can intercept XHR/fetch responses
   - Can observe MutationObserver for dynamic content

3. **Accessibility tree** — structured representation of page
   - Semantic understanding of page elements
   - Better for AI reasoning than raw HTML
   - Used by browser-use, Stagehand, and most browser agents

### Network Interception

For AI to understand and modify web traffic:

- **CDP Network domain** — monitor requests/responses without modifying Chromium
- **`webRequest` API** (MV2) — synchronous interception, can modify headers/body
- **Service Worker** — intercept at the fetch level
- **Custom proxy** — full MITM for HTTPS inspection (privacy concerns)

### Native AI Interface (Not a Chatbot)

What makes AI feel native vs. bolted-on:

1. **Address bar integration** — AI responds to natural language in the URL bar (Dia, Opera AI)
2. **Context-aware sidebar** — always knows what page you're on, can act on it
3. **Inline assistance** — highlight text, get explanation/translation without opening anything
4. **Background agents** — tasks running across tabs without user supervision
5. **Smart tab management** — AI organizes, groups, summarizes open tabs
6. **Form intelligence** — AI fills forms with context from your browsing session
7. **Keyboard-first** — everything accessible via shortcuts, command palette (Cmd+K)

### Local Model Inference in the Browser

**WebGPU + WebLLM:**
- WebLLM runs LLMs directly in the browser with WebGPU acceleration
- Approaches native GPU speeds for inference
- Supports Llama 3, Phi 3, Gemma, Mistral, Qwen
- INT-4 quantization: 75% memory reduction (Llama-3.1-8B runs on consumer hardware)
- WebGPU supported: Chrome 113+, Edge 113+, Firefox, Safari 26

**ONNX Runtime Web:**
- v2.6: WebAssembly + WebGPU backends
- Under 150KB footprint
- 10x faster than JS for compute tasks via WebAssembly
- Good for smaller models (classification, embedding, summarization)

**Practical approach for a browser:**
- **Fast tasks locally:** Summarization, classification, entity extraction via small local model
- **Complex tasks via API:** Multi-step reasoning, code generation via Claude/GPT
- **Hybrid:** Local model handles triage, routes complex queries to cloud
- **BYOM (Bring Your Own Model):** Let users connect their own endpoints (Brave Leo does this)

### Browser-Level Permission System for AI

Following Brave Leo's model:
- All AI requests proxied through anonymizing server (no IP tracking)
- Models hosted on browser company's infrastructure (not sent to model providers)
- Zero-retention configuration (conversations not stored after response)
- BYOM option: direct device-to-endpoint, bypasses browser company entirely
- Per-site AI permissions: user controls what pages AI can access
- Action confirmations for sensitive operations (purchases, form submissions)

---

## 5. Privacy Architecture

### Brave's Approach — Fingerprint Randomization

**How it works:**
- Adds subtle randomization to fingerprinting API outputs
- Randomization seed changes per session, per site (eTLD+1), per storage area
- "Poisons" fingerprint hashes — changing one value invalidates the entire composite fingerprint

**What's randomized:**
- Canvas readback (random noise added to generated images)
- WebGL debug information
- Audio context
- Device enumeration
- User Agent string (generalized)
- Battery API (returns fixed values)

**Limitation:** Randomization-based techniques are more vulnerable to motivated attackers than Firefox's fixed/standardized output approach. Brave's goal is mass surveillance prevention, not targeted attack resistance.

### Firefox's Approach — Enhanced Tracking Protection

**Layered defense:**
1. Known tracker blocking (Disconnect.me list)
2. Total Cookie Protection (cookie jar per site)
3. Canvas readback randomization (added Firefox 145, 2025)
4. Font and hardware information restrictions
5. Referrer stripping

**Result:** Firefox 145 reduces fingerprintable users by nearly half.

**Key difference from Brave:** Firefox uses privacy-by-design (limit available information) rather than privacy-by-randomization.

### Handling Cookies/Tracking Without Breaking Sites

**Brave approach:**
- JS-set cookies: 7-day maximum lifetime
- HTTP-set cookies: 6-month maximum lifetime
- Third-party cookies blocked at HTTP level
- Referrer capped to `strict-origin-when-cross-origin`

**Firefox approach:**
- Total Cookie Protection: each website gets its own cookie jar
- Third-party cookies isolated per first-party context
- State Partitioning: localStorage, IndexedDB, caches all partitioned

**Key insight:** Partition, don't block entirely. Blocking cookies breaks sites. Partitioning them per-site prevents cross-site tracking while maintaining per-site functionality.

### Tor Integration

**What Brave does:**
- Built-in Tor window (Private Window with Tor)
- `.onion` requests have empty Referer and null Origin headers
- Routes traffic through Tor network

**Key considerations for a custom browser:**
- Tor Browser is Firefox-based — would need custom implementation for Chromium
- Using Tor routing without Tor Browser's full fingerprinting protections is dangerous
- Tor significantly slows browsing (3+ relay hops)
- Better approach: offer as opt-in mode with clear performance tradeoff warning
- The Tor Project warns against using regular browsers with Tor routing — fingerprinting risk

### Local-First Data Architecture

**Principles:**
- No cloud sync by default — all data stays on device
- Bookmarks, history, passwords stored locally in encrypted database
- Optional self-hosted sync (user runs their own server)
- Optional end-to-end encrypted sync (browser company can't read data)
- AI conversations and memories stored locally (BrowserOS model)
- API keys stored in OS-level encrypted preferences (Chromium's encrypted prefs)

---

## 6. Building & Distributing a Browser

### How to Fork Chromium — The Actual Process

**Step 1: Get the code**
```bash
mkdir chromium && cd chromium
fetch --nohooks chromium
cd src
gclient runhooks
```

**Step 2: Configure**
```bash
gn gen out/Release --args='
  is_debug=false
  is_component_build=false
  proprietary_codecs=true
  ffmpeg_branding="Chrome"
  enable_widevine=true        # Requires license
  google_api_key=""            # Remove Google keys
  google_default_client_id=""
  google_default_client_secret=""
'
```

**Step 3: Build**
```bash
autoninja -C out/Release chrome
```

**Step 4: Maintain**
- DON'T make a Git fork. Maintain patches applied programmatically.
- Use a dual-repo architecture (like Brave): orchestration repo + core repo
- Keep patches minimal and well-isolated
- Chromium rebases every ~3 weeks — automation is critical

### Build System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Disk | 100GB | 500GB+ (with build artifacts) |
| RAM | 16GB | 32-64GB |
| CPU | 8 cores | 16+ cores (or distributed build) |
| Build time (local) | 3-8 hours | — |
| Build time (distributed/EngFlow) | 15 minutes | — |
| Source checkout | ~50GB | — |

**CI/CD:**
- Brave uses EngFlow for distributed builds — 8x speedup
- Pull request builder: produces artifacts at every code change
- Three channels: Nightly (daily), Beta (every 3 weeks), Release (on-demand)

### How Brave Builds and Distributes

**Build infrastructure:**
- AWS for Windows builds
- Proprietary Apple machines for macOS builds (required for code signing)
- EngFlow remote execution for Android, Linux, macOS, Windows
- 8 Android architectures built in parallel
- macOS: Universal binaries (Intel + ARM64)

**Distribution:**
- Windows: Omaha 4 (Chromium Updater) — works even when browser isn't running
- macOS: Migrating from Sparkle to Omaha 4
- Delta (differential) updates — some updates 100x smaller than full installers
- Custom forks of Google's Omaha client and Sparkle client

### Auto-Update System

**Omaha 4 (Chromium Updater):**
- Cross-platform (Windows, macOS, Linux)
- Can update when browser isn't running
- Can run with elevated privileges for system-wide installs
- Server: can self-host with `omaha-server` (open-source)

**Sparkle (macOS legacy):**
- macOS-native update framework
- Simpler but being replaced by Omaha 4

**BrowserOS approach for sidecar:**
- Independent OTA updates every 15 minutes
- Ed25519-signed binaries from R2 storage
- Zero-downtime hot-swap (new process on fresh port, proxy redirects)

### Cross-Platform Requirements

| Platform | Build Environment | Signing | Distribution |
|----------|------------------|---------|-------------|
| **macOS** | macOS + Xcode | Apple Developer Program ($99/yr), Developer ID cert, notarization via `xcrun notarytool` | DMG, Sparkle/Omaha updates |
| **Windows** | Windows + Visual Studio | EV Code Signing cert (~$300-500/yr), Microsoft SmartScreen reputation | EXE/MSI, Omaha updates |
| **Linux** | Ubuntu/Debian | GPG signing for repos | .deb, .rpm, AppImage, Snap/Flatpak |
| **Android** | Linux + Android SDK | Google Play signing | Play Store, APK sideload |
| **iOS** | macOS + Xcode | Apple Developer Program, App Store review | App Store only |

### macOS Notarization Process

1. Code-sign with Developer ID certificate
2. Upload to Apple via `xcrun notarytool submit`
3. Apple scans for malicious components
4. Staple the ticket: `xcrun stapler staple YourApp.dmg`
5. Only ZIP, DMG, or Installer Package formats accepted
6. Required since macOS 10.15 Catalina

### Team Size Estimates

| Phase | Team Size | Duration |
|-------|-----------|----------|
| **MVP (single platform)** | 3-5 engineers | 6-12 months |
| **Beta (multi-platform)** | 8-15 engineers | 12-18 months |
| **Production** | 20-40 engineers | Ongoing |
| **Brave-scale** | ~100+ engineers (289 total employees) | — |
| **Ladybird (from-scratch engine)** | 8 full-time + community | Years |

**Key roles needed:**
- Chromium/C++ engineers (the hardest to hire)
- Rust engineer (ad blocking, performance-critical systems)
- TypeScript/React (AI agent UI)
- Native platform engineers (Swift for macOS, Kotlin for Android)
- DevOps/Build engineer (CI/CD, distributed builds)
- Security engineer
- AI/ML engineer (agent orchestration, local inference)

---

## 7. Existing AI Browsers to Study

### ChatGPT Atlas (OpenAI) — The Technical Leader

**Engine:** Chromium via OWL (OpenAI Web Layer)
**Architecture:** Chromium runs as independent service process, Atlas UI in SwiftUI/AppKit
**Key innovation:** Mojo IPC between Atlas and Chromium — instant startup, crash isolation, tiny upstream diff

**Features:**
- AI sidebar for page Q&A, summarization, rewriting
- Agent Mode: autonomous multi-step task execution (booking, research, purchasing)
- Browser Memories: remembers context from sites visited, recalls later
- Auto search mode: switches between ChatGPT answers and Google results
- Tab groups, vertical tabs

**Platform:** macOS only (Windows/iOS/Android coming)
**Pricing:** Free, Plus, Pro, Go tiers (Agent Mode requires subscription)

**What they did right:** OWL architecture is brilliant — separates UI innovation from engine maintenance. Small Chromium diff means easy rebases.
**What to study:** How they handle Browser Memories (privacy implications), Agent Mode reliability.

### Perplexity Comet — The Free Alternative

**Engine:** Chromium
**Key feature:** Integrated Perplexity AI search — summarize, answer questions, fill forms, automate shopping
**Platform:** macOS, Windows, Android, iOS (March 2026)
**Pricing:** Free (Pro/Max for more features)

**Features:**
- Multi-tab assistant (summarize across all open tabs)
- Background assistants for parallel research/coding/meeting prep
- Users can choose model (Opus 4.6, Sonnet 4.5)
- Enterprise MDM deployment

**What they did right:** Making it free was smart — fastest adoption.
**What they did wrong:** Privacy concerns (cloud-based AI processing).

### Dia (Browser Company / Atlassian) — The Acquired One

**Engine:** Chromium with Swift UI
**Launched:** Beta June 2025, open to all macOS users October 2025
**Acquired:** Atlassian bought The Browser Company for $610M (September 2025)
**Pricing:** Free + $20/mo "Dialed In" tier

**Features:**
- AI in URL bar (chat + search unified)
- Third-party integrations: Slack, Notion, Google Calendar, Gmail
- AI generates reports/summaries from multiple service contexts

**What they did right:** URL bar as AI interface — natural, doesn't add UI clutter.
**What went wrong:** Arc was sunset, Dia is enterprise-pivoting under Atlassian. Consumer focus lost.

### Fellou — The Agentic One ($40M raised)

**Engine:** Chromium
**Architecture:** Browser + Workflow + Agent trinity. Eko 2.0 framework (open-source browser automation)

**Key innovations:**
- Agentic Deep Action (ADA) framework — multi-agent across platforms/tabs
- Plans tasks before acting (step-by-step action plan, then executes)
- Visual workflow inspection before execution
- "Agentic Memory" — learns from browsing behavior
- Agent Studio marketplace for custom AI agents
- Fellou CE: "spatial" browser with Z-axis UI (3D interface)
- 80% task completion on Online-Mind2web benchmark (vs 43% for competitors)

**What they did right:** Workflow visualization before execution (transparency/trust).
**What to study:** The ADA framework, multi-agent orchestration.

### Brave Leo — Privacy-First AI

**Architecture:** AI hosted on Brave's own infrastructure (including Claude models via AWS Bedrock)
**Privacy:** All requests proxied through anonymizing server, zero-retention, no data sharing with model providers

**Features:**
- Chat sidebar with page context
- Brave Search API integration for real-time results
- BYOM: connect your own model endpoint (direct device-to-endpoint)
- Multiple models: Llama, Qwen, Gemma (free), Claude, DeepSeek (premium)

**What they did right:** Privacy architecture is the best in the industry. BYOM is genius — power users bring their own models, Brave never sees the traffic.
**What to study:** Their proxy architecture, zero-retention model hosting.

### Opera AI (formerly Aria) — The Multi-Model One

**Architecture:** Rebuilt from ground up (December 2025)
**Key innovation:** Composer engine — automatically routes queries to best model (Aria, Gemini, ChatGPT)

**Features:**
- "Ask AI" button in toolbar (replaced sidebar)
- Side panel for AI (doesn't overlay content)
- Context-aware: interacts with page content, open tabs
- Creates Tab Islands for organization
- Opera Neon: separate agentic browser ($19.90/mo, 4 specialized agents)

**What they did right:** Multi-model routing is smart — different models excel at different tasks.

### BrowserOS — The Open-Source Reference

**Engine:** Chromium fork with C++ patches
**Architecture:** Three-process model (Agent/Browser/Sidecar)
**MCP server:** 53+ browser tools exposed to external AI clients
**Privacy:** All AI operations local or via user API keys

**What to study:** This is the most transparent AI browser architecture available. The entire codebase is open-source. Study their:
- C++ patch approach for Chromium modifications
- Extension-based agent with Controller bridge pattern
- MCP server implementation
- Memory system (CORE.md, daily notes, SOUL.md personality)
- Hot-swap sidecar update mechanism

**GitHub:** https://github.com/browseros-ai/BrowserOS

### Other Notable Entries (2026)

- **Genspark:** 169+ open-weight models running ON-DEVICE, MCP Store with 700+ tools, $160M raised
- **Sigma AI Browser:** Free, local-first, cross-platform, no cloud dependency
- **Google Chrome Auto Browse:** Gemini 3 in Chrome for Premium subscribers (January 2026)
- **Claude for Chrome:** Extension (not browser), reduced prompt injection from 23.6% to 11.2%
- **Google Disco:** Experimental — generates custom web apps from open tabs (GenTabs)

### What Features Do Users Actually Want?

**Survey data (2025-2026):**
- 49%: Research support (summarize, explain, compare)
- 37%: Automating routine actions (form filling, data extraction)
- 34%: Drafting personalized messages
- 67%: Upload files and get document-specific answers
- 61%: Persistent memory across sessions
- 58%: Advanced source filtering (academic vs informal)
- 52%: Control over response length
- 92%: More personalization and control
- 45%: Privacy is the #1 barrier to AI adoption
- 35%: Lack of trust in AI accuracy

**The killer features are:** research assistance, task automation, and memory — with privacy as the non-negotiable requirement.

---

## 8. Strategic Recommendations

### Recommended Architecture for Silver Browser

Based on all research, here's what I'd recommend:

**Engine:** Fork Chromium, but use the OWL-style architecture (Atlas approach):
- Run Chromium as a service process
- Build UI natively (Swift on macOS, or cross-platform with Tauri/Rust)
- Communicate via Mojo IPC
- Ship Chromium as prebuilt binary — most engineers never touch it
- Minimal Chromium patches = easy upstream rebases

**Ad Blocking:** Integrate `adblock-rust` (Brave's library) at the network layer:
- Open-source, proven at scale, 5.7us per request
- Supports all major filter lists
- Add YouTube-specific heuristics (manifest parsing, segment skipping)
- Ship filter list updates OTA (independent of browser updates)

**AI Architecture:** Hybrid BrowserOS + Atlas approach:
- Native AI sidebar (not an extension chatbot)
- CDP-based DOM access for page understanding
- Background agents for multi-tab automation
- Local model for fast tasks (summarization, classification via WebLLM)
- Cloud API for complex reasoning (BYOM — user brings their own key)
- MCP server for external tool integration
- Memory system: local-first, daily notes + persistent facts

**Privacy:**
- Strip all Google services (use Brave's deviations list as template)
- Built-in fingerprint protection (hybrid: Brave randomization + Firefox standardization)
- Total Cookie Protection (partition per site, don't block)
- Zero-retention AI processing
- All data local by default
- Optional E2E encrypted sync

**Performance:**
- Aggressive tab hibernation (85% memory savings per tab)
- No extension overhead (AI is native)
- Ad blocking saves 30-50% of network requests
- Skia Graphite for GPU rendering
- Prebuilt Chromium binary for instant startup
- Predictive preloading via AI

### Timeline Estimate

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1** | 3-4 months | Chromium fork builds, Google services stripped, basic ad blocking |
| **Phase 2** | 3-4 months | AI sidebar integration, CDP-based page understanding, local model |
| **Phase 3** | 3-4 months | Agent mode (multi-step automation), memory system, BYOM |
| **Phase 4** | 3-4 months | Cross-platform (Windows/Linux), auto-updates, polish |
| **Alpha** | ~6 months | Single platform, core features |
| **Beta** | ~12 months | Multi-platform, agent mode, ad blocking |
| **v1.0** | ~18 months | Production-ready with full feature set |

### Minimum Viable Team

- 1 Chromium/C++ engineer (build system, patches, engine work)
- 1 Rust engineer (ad blocking, performance systems)
- 1 Full-stack/AI engineer (agent, sidebar, LLM orchestration)
- 1 Native UI engineer (Swift/platform UI)
- 1 DevOps (CI/CD, distributed builds, updates)
- Total: 5 engineers for MVP

---

## Key Sources

### Browser Engines
- [How to Fork Chromium](https://omaha-consulting.com/how-to-fork-chromium)
- [Brave Deviations from Chromium](https://github.com/brave/brave-browser/wiki/Deviations-from-Chromium-(features-we-disable-or-remove))
- [Servo January 2026 Update](https://www.phoronix.com/news/Servo-January-2026)
- [Servo Official Site](https://servo.org/)
- [Ladybird Browser](https://ladybird.org/)
- [Ladybird — New Browser Engine Coming 2026](https://www.makeuseof.com/ladybird-new-browser-engine-coming-2026/)
- [Arc Browser Wikipedia](https://en.wikipedia.org/wiki/Arc_(web_browser))
- [Browser Engines 2025](https://digitechbytes.com/tech-basics-evergreen-fundamentals/browser-engines-2025/)
- [Fastest Browser 2026 Benchmarks](https://kahana.co/blog/fastest-web-browser-2026-benchmarks-caveats-real-world-problems)

### Ad Blocking
- [Brave adblock-rust GitHub](https://github.com/brave/adblock-rust)
- [Brave 69x Ad Blocker Performance](https://brave.com/blog/improved-ad-blocker-performance/)
- [Brave Adblock Memory Reduction](https://brave.com/privacy-updates/36-adblock-memory-reduction/)
- [Manifest V3 Ad Blocker Impact](https://adblock-tester.com/ad-blockers/manifest-v3-ad-blocker-impact/)
- [YouTube SSAI — AdGuard Analysis](https://adguard.com/en/blog/youtube-server-side-ad-insertion.html)
- [YouTube Ad Blockers 2026](https://adblock-tester.com/ad-blockers/youtube-ad-blockers-that-still-work-in-2025/)

### Performance
- [Chromium Efforts Against Memory Bloat](https://www.chromium.org/developers/memory-bloat/)
- [Skia Graphite Introduction](https://blog.chromium.org/2025/07/introducing-skia-graphite-chromes.html)
- [Building and Releasing Brave](https://brave.com/blog/building-brave/)
- [EngFlow + Brave Case Study](https://www.engflow.com/caseStudies/brave)

### AI Integration
- [BrowserOS DeepWiki](https://deepwiki.com/browseros-ai/BrowserOS)
- [BrowserOS GitHub](https://github.com/browseros-ai/BrowserOS)
- [OpenAI OWL Architecture (Atlas)](https://openai.com/index/building-chatgpt-atlas/)
- [Atlas Architecture — ByteByteGo](https://blog.bytebytego.com/p/the-architecture-behind-atlas-openais)
- [WebLLM Documentation](https://webllm.mlc.ai/docs/)
- [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/)
- [Brave Leo Roadmap](https://brave.com/blog/leo-roadmap-2025-update/)
- [Brave BYOM](https://brave.com/blog/byom-nightly/)

### Privacy
- [Brave Fingerprint Randomization](https://brave.com/privacy-updates/3-fingerprint-randomization/)
- [Brave Fingerprinting Protections Wiki](https://github.com/brave/brave-browser/wiki/Fingerprinting-Protections)
- [Firefox Fingerprinting Protections](https://blog.mozilla.org/en/firefox/fingerprinting-protections/)
- [Firefox Enhanced Tracking Protection](https://support.mozilla.org/en-US/kb/enhanced-tracking-protection-firefox-desktop)

### Building & Distribution
- [Building Chromium from Source](https://copyprogramming.com/howto/build-chromium-from-source)
- [Omaha 4 Tutorial](https://omaha-consulting.com/chromium-updater-omaha-4-tutorial)
- [Apple Notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Chromium Hardware Requirements](https://www.chromium.org/chromium-os/developer-library/getting-started/hardware-requirements/)

### AI Browser Landscape
- [Agentic Browser Landscape 2026](https://nohacks.co/blog/agentic-browser-landscape-2026)
- [ChatGPT Atlas — OpenAI](https://openai.com/index/introducing-chatgpt-atlas/)
- [Perplexity Comet](https://www.perplexity.ai/comet)
- [Dia Browser Wikipedia](https://en.wikipedia.org/wiki/Dia_(web_browser))
- [Fellou AI Browser](https://fellou.ai/blog/how-fellou-redefines-ai-browser-with-agentic-automation/)
- [Opera AI Features](https://blogs.opera.com/news/2025/12/opera-ai-comes-to-opera-one-opera-gx-opera-air/)
- [AI Browser Benchmark Guide 2026](https://aimultiple.com/ai-web-browser)
- [What Users Want from AI Browsers](https://shift.com/blog/the-2026-state-of-browsing-report-is-here/)
