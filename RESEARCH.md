# Computer Use / GUI Agent — Research & Benchmarks (Early 2026)

Research compiled March 2026. Numbers sourced from official leaderboards, papers, and vendor announcements.

---

## 1. OSWorld Benchmark

**What it is:** The standard benchmark for evaluating computer use agents. 369 real-world tasks on real operating systems (Ubuntu Linux primarily, also Windows and macOS). Tasks span Chrome, LibreOffice, VS Code, Thunderbird, GIMP, file management, etc.

**Scoring methodology:** Binary task success via execution-based validation scripts. Custom scripts inspect the resulting OS/application state (output artifacts, app settings, files, etc.) to determine if the task was completed. No subjective evaluation — purely programmatic verification. Fractional rewards may be granted where supported.

**Human baseline:** ~72.4%

**OSWorld-Verified** (July 2025 update): Cleaned-up version with fixed annotation bugs, AWS parallelization support, and officially verified evaluation runs.

### Leaderboard — OSWorld-Verified (as of early 2026)

| Rank | Model / Agent | Score (%) | Date |
|------|--------------|-----------|------|
| 1 | GPT-5.4 (OpenAI) | 75.0 | ~Feb 2026 |
| 2 | Claude Opus 4.6 (Anthropic) | 72.7 | ~Jan 2026 |
| 3 | Claude Sonnet 4.6 (Anthropic) | 72.5 | ~Jan 2026 |
| 4 | Claude Sonnet 4.5 | 61.4 | ~Sep 2025 |
| 5 | CoACT-1 | 60.8 | ~2025 |
| — | Human baseline | 72.4 | — |

Average across all verified models: ~59.9%

### Leaderboard — Standard OSWorld (self-reported, various step limits)

| Model / Agent | Score (%) | Steps | Date |
|--------------|-----------|-------|------|
| OSAgent (TheAGI Co.) | 76.3* | — | Oct 2025 |
| AskUI VisionAgent | 66.2 | — | Nov 2025 |
| GTA1 w/ o3 | 45.2 | — | ~2025 |
| OpenAI CUA (o3) | 42.9 | — | ~2025 |
| UI-TARS-1.5 (ByteDance) | 42.5 | 100 | Apr 2025 |
| OpenAI CUA | 38.1 | — | Jan 2025 |
| Agent S2 + Claude 3.7 | 34.5 | 50 | Mar 2025 |
| Claude 3.7 Sonnet | 28.0 | 100 | Feb 2025 |

*OSAgent claims 76.3% (274.52/360), superhuman. Self-reported, not officially verified.

---

## 2. WebArena / VisualWebArena

### WebArena
812 realistic web tasks across self-hosted websites (shopping, Reddit, GitLab, Wikipedia, map, CMS admin). Tests autonomous web navigation, form filling, information retrieval, multi-step workflows. Human performance ~78.2%.

| Model / Agent | Score (%) | Date |
|--------------|-----------|------|
| OpenAI CUA | 58.1 | Jan 2025 |
| Human baseline | 78.2 | — |

### WebVoyager (related web benchmark)

| Model / Agent | Score (%) | Date |
|--------------|-----------|------|
| OpenAI CUA | 87.0 | Jan 2025 |
| UI-TARS-1.5 | 84.8 | Apr 2025 |
| Claude 3.7 | 84.1 | Feb 2025 |
| Google Mariner | 83.5 | ~2025 |

### VisualWebArena
910 tasks across 3 web apps requiring explicit visual understanding (classifieds, shopping, Reddit). Multimodal — agents must reason about images on pages, not just text. Detailed 2026 leaderboard scores not readily available in public sources.

### Online-Mind2Web

| Model / Agent | Score (%) | Date |
|--------------|-----------|------|
| UI-TARS-2 | 88.2 | Sep 2025 |
| UI-TARS-1.5 | 75.8 | Apr 2025 |
| OpenAI CUA | 71.0 | — |
| Claude 3.7 | 62.9 | — |

---

## 3. Claude Computer Use (Anthropic)

### Architecture
- **Screenshot-based perception-action loop**: Takes a screenshot, analyzes with vision, decides next action.
- Reads actual current screen state at each step — no memory of past UI layouts.
- **Action space**: Mouse (move, click, double-click, drag), keyboard (type, key combos), scroll.
- **Zoom action** (newer models): Can inspect detailed screen regions.
- System prompt adds ~466-499 tokens for computer use tool definition.
- Available on: Claude Opus 4.6, Claude Sonnet 4.6, Claude Sonnet 4.5.

### Benchmark Scores

| Benchmark | Score (%) | Model | Date |
|-----------|-----------|-------|------|
| OSWorld-Verified | 72.7 | Opus 4.6 | ~Jan 2026 |
| OSWorld-Verified | 72.5 | Sonnet 4.6 | ~Jan 2026 |
| OSWorld-Verified | 61.4 | Sonnet 4.5 | ~Sep 2025 |
| OSWorld | 28.0 | Sonnet 3.7 (100 steps) | Feb 2025 |
| WebVoyager | 84.1 | Sonnet 3.7 | Feb 2025 |
| SWE-bench Verified | 80.9 | Opus 4.5 | ~2025 |

### Historical Progression (OSWorld)
14.9% (Sonnet 3.5) -> 28.0% (Sonnet 3.5 v2) -> 42.2% (Sonnet 3.6) -> 61.4% (Sonnet 4.5) -> 72.5% (Sonnet 4.6)

### Cost
- **API pricing (Sonnet 4.6):** $3/M input tokens, $15/M output tokens
- **API pricing (Opus 4.6):** $5/M input tokens, $25/M output tokens
- **Per-action estimate:** Each step involves sending a screenshot (~1000-2000 tokens for image) plus conversation context. A typical 15-step task with Sonnet costs roughly $0.05-0.20. Long multi-step tasks (50-100 steps) can cost $1-5+.
- **Subscriptions:** Claude Pro $20/month; Claude Code Max $200/month (~$6/day average API-equivalent usage)

### Latency
- Each screenshot-analyze-act cycle: ~3-10 seconds per action depending on model and context length.
- Slower than hardcoded selectors because it reasons about the visual layout each step.

### Known Limitations
- Can only act on what is currently visible on screen.
- Can misidentify UI elements, especially in dense or unfamiliar interfaces.
- Actions can land in the wrong pixel location.
- Non-deterministic — same task may succeed or fail on different runs.
- No persistent memory across sessions.
- High latency compared to traditional automation.

---

## 4. OpenAI Computer Use / Operator

### What they released
- **Operator** (Jan 2025): Consumer product for web-based tasks. Available to ChatGPT Pro ($200/month).
- **CUA (Computer-Using Agent)**: Underlying model/API. Screenshot-based GUI interaction.
- **CUA API**: Developer access for building custom agents.

### Architecture
- Screenshot-based perception -> action loop (same paradigm as Claude).
- Built on GPT-4o/o3 family models.
- Security: Takeover Mode (sensitive ops), Watch Mode, instant data wiping.
- Browser-in-the-cloud architecture for the Operator product.

### Benchmark Scores

| Benchmark | Score (%) | Model/Version | Date |
|-----------|-----------|---------------|------|
| OSWorld-Verified | 75.0 | GPT-5.4 | ~Feb 2026 |
| OSWorld | 42.9 | CUA (o3) | ~2025 |
| OSWorld | 38.1 | CUA (original) | Jan 2025 |
| WebArena | 58.1 | CUA | Jan 2025 |
| WebVoyager | 87.0 | CUA | Jan 2025 |

### Cost
- **Operator:** $200/month (ChatGPT Pro).
- **API (GPT-5.2):** $1.75/M input, $14/M output tokens.
- Per-task cost not officially published; comparable to Claude for API usage.

### Latency
- Several seconds per action in the perception-action loop.
- Operator adds cloud rendering overhead.

### Limitations
- Struggles with complex multi-step tasks (calendar management, slide decks noted as weak points).
- Initially a research preview; production API came later.

---

## 5. Google Mariner / Project Jarvis

### What it is
- **Project Mariner**: Google DeepMind's browser-use AI agent, powered by Gemini.
- **Project Jarvis**: Earlier internal project name for broader computer-use.
- Can handle up to 10 simultaneous tasks.
- "Teach & Repeat" functionality for learning workflows.
- 2M token context window.
- Rolled out at Google I/O (May 2025). Available as Chrome extension.

### Benchmark Scores

| Benchmark | Score (%) | Date |
|-----------|-----------|------|
| WebVoyager | 83.5 | ~2025 |

Limited publicly reported scores compared to Claude and OpenAI. Mariner is primarily a browser agent, not a full desktop computer-use agent. No OSWorld scores published.

---

## 6. UI-TARS (ByteDance)

### UI-TARS-1.5 (April 2025)
Open-source multimodal agent. Qwen2.5-VL architecture + reinforcement learning reasoning. 7B model released on HuggingFace.

**Online Benchmark Comparison:**

| Benchmark | UI-TARS-1.5 | OpenAI CUA | Claude 3.7 | Prev. SOTA |
|-----------|-------------|------------|------------|------------|
| OSWorld (100 steps) | **42.5** | 36.4 | 28.0 | 38.1 (200 step) |
| Windows Agent Arena (50 steps) | **42.1** | — | — | 29.8 |
| WebVoyager | 84.8 | **87.0** | 84.1 | 87.0 |
| Online-Mind2Web | **75.8** | 71.0 | 62.9 | 71.0 |
| Android World | **64.2** | — | — | 59.5 |

**Grounding Capability:**

| Benchmark | UI-TARS-1.5 | OpenAI CUA | Claude 3.7 | Prev. SOTA |
|-----------|-------------|------------|------------|------------|
| ScreenSpot-V2 | **94.2** | 87.9 | 87.6 | 91.6 |
| ScreenSpotPro | **61.6** | 23.4 | 27.7 | 43.6 |

**Model Scale Comparison:**

| Benchmark | UI-TARS-72B-DPO | UI-TARS-1.5-7B | UI-TARS-1.5 (full) |
|-----------|-----------------|----------------|---------------------|
| OSWorld | 24.6 | 27.5 | **42.5** |
| ScreenSpotPro | 38.1 | 49.6 | **61.6** |

### UI-TARS-2 (September 2025)
Major upgrade: multi-turn RL, "All in One" agent (GUI + Game + Code + Tool Use).

| Benchmark | UI-TARS-2 (%) |
|-----------|---------------|
| OSWorld | 47.5 |
| Online-Mind2Web | 88.2 |
| Windows Agent Arena | 50.6 |
| Android World | 73.3 |

### Cost
- Open-source 7B model on HuggingFace. Self-hosted, no API cost.
- Requires ~16GB+ VRAM for 7B model.

---

## 7. Other Notable Agents & Benchmarks

### SWE-bench (Coding Agents)

SWE-bench Verified: 500 curated Python issues. SWE-bench Pro: harder, less contaminated.

| Agent / Model | SWE-bench Verified (%) | SWE-bench Pro (%) |
|--------------|----------------------|-------------------|
| Claude Opus 4.5 | 80.9 | — |
| Sonar Foundation Agent | 79.2 | — |
| OpenAI GPT-5 | — | 23.3 |
| Claude Opus 4.1 | — | 23.1 |

Note: SWE-bench Verified is considered contaminated. SWE-bench Pro scores are dramatically lower and more realistic.

### Windows Agent Arena

| Model | Score (%) |
|-------|-----------|
| UI-TARS-2 | 50.6 |
| UI-TARS-1.5 | 42.1 |
| Previous SOTA | 29.8 |

### Android World

| Model | Score (%) |
|-------|-----------|
| UI-TARS-2 | 73.3 |
| UI-TARS-1.5 | 64.2 |
| Previous SOTA | 59.5 |

### ScreenSpot-V2 / ScreenSpotPro (GUI Grounding)

| Model | ScreenSpot-V2 (%) | ScreenSpotPro (%) |
|-------|-------------------|-------------------|
| UI-TARS-1.5 | 94.2 | 61.6 |
| UI-TARS-1.5-7B | — | 49.6 |
| OpenAI CUA | 87.9 | 23.4 |
| Claude 3.7 | 87.6 | 27.7 |

---

## 8. Key Takeaways for the Ghost Project

1. **OSWorld is the gold standard** — 369 tasks, execution-based scoring, human baseline 72.4%. Top agents are now at/above human level.

2. **Claude Sonnet 4.6 is the best cost/performance for computer use** — 72.5% OSWorld-Verified at Sonnet pricing ($3/$15 per M tokens), nearly matching Opus 4.6 (72.7%).

3. **UI-TARS-1.5-7B is the best open-source option** — 27.5% on OSWorld with just a 7B model. The full UI-TARS-1.5 hits 42.5%. Based on Qwen2.5-VL (relevant to your architecture choice).

4. **The gap between 7B open-source (~27%) and frontier closed-source (~73-75%) is massive** — roughly 45-48 percentage points. This is the gap LoRA + GRPO training would need to narrow.

5. **Grounding is where open-source shines** — UI-TARS-1.5 dominates ScreenSpotPro at 61.6% vs Claude's 27.7% and OpenAI's 23.4%. Open-source models can beat closed-source on element localization even when trailing on end-to-end tasks.

6. **Cost per task (API agents):** ~$0.05-0.20 for simple 15-step tasks, $1-5+ for complex 50-100 step tasks. Self-hosted 7B model eliminates per-task cost entirely.

7. **UI-TARS-1.5-7B scores 49.6% on ScreenSpotPro** — a 7B model beating both Claude (27.7%) and OpenAI CUA (23.4%) on grounding. This validates the Qwen2.5-VL + RL approach at small scale.

---

## Existing Research from Previous Sessions

### Models (Vision + Grounding)

| Model | Size | ScreenSpot-Pro | Approach | Key Insight |
|-------|------|---------------|----------|-------------|
| GTA1-72B (GRPO) | 72B | 58.4% | RL-trained coordinate generation | GRPO beats SFT by 5-7% |
| GUI-Cursor-7B | 7B | 56.5% | Coordinate token generation | Specialized cursor model |
| GUI-Actor-7B | 7B | 44.6% | Coordinate-FREE (attention-based) | Beats UI-TARS-72B (38.1%) |
| GUI-Eyes-3B | 3B | 44.8% | RL with 3K samples | Tiny data, big results |
| UI-TARS-1.5-7B | 7B | 61.6% | End-to-end, 50B tokens training | ByteDance |
| OS-Atlas-7B | 7B | 18.9% | SFT on 13M elements | Strong base, weak on Pro |
| ShowUI-2B | 2B | ~30% est | Token selection, 256K samples | Most efficient |
| CogAgent-18B | 18B | N/A | Dual-encoder cross-attention | First GUI-specialized VLM |
| SeeClick-9.6B | 9.6B | N/A | LoRA on Qwen-VL | Created ScreenSpot benchmark |

### Frameworks (Agent Loops)

| Framework | Vision | Actions | Planning | Local? |
|-----------|--------|---------|----------|--------|
| Cradle (Skywork) | GPT-4o screenshots | Python -> mouse/kb | 6-module pipeline + skill library | No |
| UFO (Microsoft) | Screenshots + Windows UIA | GUI + native APIs | Dual-agent ReAct | No |
| AppAgent (Tencent) | Screenshots + XML | 5 element-based actions | Explore -> Learn -> Execute | No |
| WebVoyager | Screenshots + SoM | 7 Selenium actions | ReAct loop | No |
| Claude Computer Use | Screenshots (pixel counting) | 15+ mouse/kb actions | Native model capability | No |
| OpenAdapt | Screenshots + SAM | Recorded action replay | Demo-conditioned | Partially |
| Open Interpreter | Screenshots (OS mode) | Code execution | Implicit via LLM | Yes (with local model) |

### Training Data Landscape

| Dataset | Size | Platform | Type |
|---------|------|----------|------|
| OS-Atlas Corpus | 13.58M elements, 2.3M screenshots | Web/Win/Android/Linux/Mac | Grounding |
| AITW | 715K episodes, 30K tasks | Android | Navigation + grounding |
| Mind2Web | 2K+ tasks, 137 websites | Web | Navigation |
| Rico/CLAY | 66K screens | Android | UI structure |
| ScreenSpot/v2/Pro | 600-1,581 samples | All platforms | Evaluation |
| CCS400K | 400K pages, 140M QA pairs | Web | Grounding |
| UGround | 10M+ elements | Web | Grounding |

### Innovation Opportunities

1. **Coordinate precision**: Best models miss 40%+ on pro software (ScreenSpotPro). Small UI elements (0.07% screen area) nearly impossible.
2. **Latency**: Cloud frameworks add 1-5s per action. No optimized local inference pipeline exists.
3. **End-to-end local**: Every strong framework depends on cloud APIs. No production-quality local autonomous agent exists.
4. **Training efficiency**: GUI-Eyes-3B achieved 44.8% on ScreenSpotPro with just 3K samples via GRPO. Nobody has combined efficient RL with coordinate-free grounding.

### Architecture Strategy: Coordinate-Free Grounding

Three approaches exist:
1. **Tokenized coordinates** (most common): Model outputs `(523, 217)` as text. Used by CogAgent, SeeClick, OS-Atlas, UI-TARS, Qwen2.5-VL. Weak spatial-semantic alignment.
2. **Coordinate-free / attention-based** (GUI-Actor): `<ACTOR>` token attends to visual patches. Only ~100M new params on frozen Qwen2.5-VL. Beats 72B models at 7B scale.
3. **Ruler tokens**: Auxiliary tokens encode pixel coordinates via positional embeddings. <1% token overhead.

---

## Sources

- [OSWorld Official Site & Leaderboard](https://os-world.github.io/)
- [OSWorld-Verified Announcement](https://xlang.ai/blog/osworld-verified)
- [OSWorld GitHub](https://github.com/xlang-ai/OSWorld)
- [OSWorld-Verified Leaderboard (LLM Stats)](https://llm-stats.com/benchmarks/osworld-verified)
- [OSWorld Leaderboard (LLM Stats)](https://llm-stats.com/benchmarks/osworld)
- [UI-TARS GitHub & README](https://github.com/bytedance/UI-TARS)
- [UI-TARS-2 Paper](https://arxiv.org/abs/2509.02544)
- [UI-TARS-1.5 Blog](https://seed-tars.com/1.5)
- [WebArena GitHub](https://github.com/web-arena-x/webarena)
- [OpenAI CUA Announcement](https://openai.com/index/computer-using-agent/)
- [OpenAI Operator Launch (MIT Tech Review)](https://www.technologyreview.com/2025/01/23/1110484/openai-launches-operator-an-agent-that-can-use-a-computer-for-you/)
- [Project Mariner — Google DeepMind](https://deepmind.google/models/project-mariner/)
- [Claude Computer Use Tool Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- [Claude Sonnet 4.6 Announcement](https://www.anthropic.com/news/claude-sonnet-4-6)
- [SWE-bench Leaderboard](https://www.swebench.com/)
- [SWE-bench Verified (Epoch AI)](https://epoch.ai/benchmarks/swe-bench-verified)
- [O-Mega 2025-2026 AI Computer-Use Guide](https://o-mega.ai/articles/the-2025-2026-guide-to-ai-computer-use-benchmarks-and-top-ai-agents)
- [TheAGI Company — OSAgent](https://www.theagi.company/blog/osworld)
- [AskUI Benchmarks](https://www.askui.com/benchmarks)
- [OSWorld-Human Paper](https://arxiv.org/html/2506.16042v1)
- [Epoch AI — What OSWorld Tells Us](https://epoch.ai/blog/what-does-osworld-tell-us-about-ais-ability-to-use-computers)
