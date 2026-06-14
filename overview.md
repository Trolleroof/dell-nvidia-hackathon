# FactoryMind — Project Overview

**The single source of truth for the project.** Start here, then drop into the role-specific docs for detail.

| | |
|---|---|
| **Project** | FactoryMind — an always-on, fully-local controller agent for a multi-robot assembly cell |
| **Model** | DiffusionGemma (hero) + Gemma 4 autoregressive (baseline), both served locally |
| **Hardware** | Dell Pro Max with GB10 (Grace Blackwell, 128 GB unified, aarch64 / DGX OS) |
| **Event** | Dell × NVIDIA "Local AI on Dell Pro Max with GB10" hackathon · June 14, 2026 · build 10:00 → 18:00 |
| **Team** | 4 roles — A (Sim) · B (Agent) · C (Frontend) · D (Models & Box) |
| **Detailed roles** | [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md) |

---

## 1. The Problem and the Solution

**Problem.** A factory floor can't run its control intelligence in the cloud. Two hard constraints make cloud a non-starter: the cell's operational data (layouts, parts, processes, camera frames) can't leave the premises, and a real-time control loop can't tolerate a network round-trip on every decision. The result today is brittle, hard-coded automation that can't reason or replan.

**Solution.** A single persistent agent runs the entire control loop **on the box** — local, always-on, and fast. In Phase 1 it reads structured sim state plus a text instruction such as "sort the green boxes," asks DiffusionGemma for the next coordinated action across all robots, validates the output against a hard schema, steps the cell, and repeats. No data leaves the device; no decision waits on the network.

**The on-theme insight.** DiffusionGemma generates a whole block of tokens *in parallel* per pass instead of one at a time. We frame each control decision as a structured block — all N robots' next moves in a single parallel generation pass. **Parallel generation for parallel control.** This is exactly the kind of single-user, low-latency local workload the GB10 exists to sell, and exactly what cloud inference is worst at.

---

## 2. Main Goal

Ship a working **always-on, fully-local multi-robot controller** and prove the thesis on stage: a live, side-by-side **diffusion-vs-autoregressive latency dashboard** where the diffusion-driven cell keeps moving while the AR baseline lags — running entirely on the GB10, with nothing going to the cloud.

The win condition for the judges (Dell + NVIDIA executives) is a demo that shows **why this specific local box matters** — on-prem data, low latency, and a capability the cloud structurally can't match.

> **North-star ship order:** (1) sim + NemoClaw loop with a mock endpoint on a laptop → (2) same loop on the box with AR Gemma 4 → (3) latency dashboard → (4) DiffusionGemma hero path *if* 1–3 are green → (5) Phase 2 VLA/video perception only if everything else is already working. There is always a working demo at each step.

---

## 3. The Four Roles (summary)

| Role | Owner of | In one line |
|---|---|---|
| **A — Simulation** | The cell | MuJoCo: 2 arms, one pick-and-place task, exposes `get_state()` / `step()` as NemoClaw tools and a deterministic oracle policy. |
| **B — Agent** | Tools + schema | Defines the NemoClaw tool set (`get_state`, `step`, `hold_position`) that NemoClaw calls, owns the action schema (C1), and extracts telemetry (C5) from NemoClaw agent logs. |
| **C — Frontend** | The proof | The local diffusion-vs-AR latency dashboard plus the cell visualization — NemoClaw's control UI (`:8080`) is embedded or linked within the dashboard. |
| **D — Models & Box** | Inference + hardware | Weights on SSD, local OpenAI-compatible serving, NemoClaw bring-up, install scripts, and the GB10 first-hour gate. |

Full responsibilities, workflows, and failure handling for each are in [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md) (see §6 for direct links).

---

## 4. How the Roles Interact

Everything composes through **five frozen contracts** (defined in full in the roles doc, §"Shared Contracts"). Freeze these before anyone goes heads-down — they are why four people can build in parallel against mocks and merge cleanly.

- **C1 — Action schema** (`CellPlan`): the model's output and the only thing the sim accepts. *A + B co-own.*
- **C2 — Sim-state schema**: what `get_state()` returns; exposed as the `get_state` NemoClaw tool payload. Phase 1 includes ground-truth object attributes such as id, color, position, and location so text tasks like "sort green boxes" do not require camera perception. *A owns.*
- **C3 — NemoClaw tool definitions**: the three tools NemoClaw calls (`get_state`, `step`, `hold_position`), their JSON schemas, and the tool server port. *B owns; configured only through NemoClaw profiles.*
- **C4 — Endpoint contract**: `base_url`, model name, structured-output support, `max_model_len`. *D owns, hands to B (and NemoClaw config).*
- **C5 — Telemetry JSONL**: one line per control step, extracted from NemoClaw agent logs; the dashboard's only data source. *B owns, C consumes.*

```
   A (Sim) ◀──────────────────────────────────────────────────────────────┐
   tools: get_state / step / hold_position (C3, served by B)              │
        │                                                                  │
        ▼                                                                  │
   NemoClaw agent (harness) ──prompt──▶ D (Models): :8000 / :8001
        │  text task + structured state; tool calls      diffusion / AR
        │ C5 telemetry JSONL (extracted from NemoClaw logs)
        ▼
   C (Frontend): latency dashboard + NemoClaw control UI (:8080)
        browser on the box — no cloud, no SSH X-forwarding
   D (Box) ── C4 endpoints ─▶ NemoClaw config     D ── GL/EGL stack ─▶ A
```

The dependency seams, in build order of risk: **A-B** (closeable through the NemoClaw mock profile + smoke test) -> **B-C** (closeable via NemoClaw telemetry replay, no GPU) -> **D-NemoClaw** (the last and riskiest seam, so bring up AR Gemma 4 first to unblock everyone).

---

## 5. End-to-End Workflow

**Runtime control loop (the always-on agent — orchestrated by NemoClaw):**

1. **Read** — NemoClaw calls the `get_state` tool (B's tool server) → current cell state (C2) returned as tool result, including object ids/colors/positions for Phase 1 sorting tasks.
2. **Plan** — NemoClaw prompts the local model (D's endpoint, C4) with the user text task, structured state, and tool schema; model returns a `CellPlan` (C1) as a tool call or structured output.
3. **Parse + validate** — NemoClaw/B's tool server enforces the schema on `step` invocation; on bad args, the tool returns an error and NemoClaw reprompts once; on a second failure, `hold_position` tool is called instead. The loop never blocks.
4. **Step** — NemoClaw calls the `step` tool with the validated `CellPlan`; physics advances; events emit (pick success, collision, task complete).
5. **Log** — B's telemetry extractor reads NemoClaw agent logs and emits one C5 JSONL line per step: latency, TTFT, tokens, parse result, action summary, sim event.
6. **Render** — C's dashboard reads the telemetry stream and A's frames; NemoClaw's own control UI (`:8080`) is embedded or linked alongside.
7. **Repeat** — NemoClaw keeps the agent loop running, always-on.

For the hero moment, NemoClaw runs two parallel agent sessions over identical state — one pointed at DiffusionGemma (`:8000`), one at AR Gemma 4 (`:8001`) — and the dashboard shows both clocks side by side.

**Build-time sequence:** follow the north-star ship order (§2). Laptop-green (NemoClaw mock endpoint + oracle-backed sim + replay all working) **before** first contact with the box.

---

## 6. Architecture and Technology Stack

```
                    Dell Pro Max with GB10 (128 GB unified, aarch64 / DGX OS)
 ┌───────────────────────────────────────────────────────────────────────────┐
 │  MuJoCo cell (A)      Tool API / C2 state (B)   NemoClaw + Models (D)     │
 │  ┌─────────────┐ tool  ┌──────────────────────────┐  /v1 ┌─────────────┐  │
 │  │ 2 robot arms│◀─────▶│ get_state: objects      │─────▶│DiffusionGemma│ │
 │  │ parts, bins │ calls │ id/color/pos/location   │      │  :8000 NVFP4│  │
 │  │ get_state() │       │ text task + tool schema │◀─────│Gemma 4 AR   │  │
 │  │ step()      │       │ NemoClaw calls tools    │      │  :8001      │  │
 │  └──────┬──────┘       │ step / hold_position    │      └─────────────┘  │
 │         │ frames       └────────────┬───────────────┘                       │
 │         │                          │ C5 telemetry JSONL (from NemoClaw logs)│
 │         ▼                          ▼                                        │
 │  C (Frontend): latency dashboard + NemoClaw control UI (:8080) embedded    │
 │                browser on the box — diffusion vs AR, live                  │
 └───────────────────────────────────────────────────────────────────────────┘
              No outbound internet during the demo — that's the point.
```

**Stack by layer:**

- **Simulation (A):** MuJoCo (`mujoco` Python bindings, MJCF scenes, offscreen/EGL rendering), NumPy. Phase 1 exposes ground-truth object state, including color labels for sorting tasks; fallback engine: PyBullet.
- **Agent harness (NemoClaw):** NemoClaw calls B's tool server to drive the sim. No custom Python control loop — NemoClaw *is* the loop.
- **Tool server (B):** Python + FastAPI + Pydantic v2. Exposes three tools: `get_state` → C2 state, `step(CellPlan)` → sim advance, `hold_position` → no-op safety. Also runs a telemetry extractor that tails NemoClaw logs → C5 JSONL.
- **Frontend (C):** React/TypeScript + Vite + Tailwind + charting lib for the polished build; static-HTML + vanilla-JS fallback. Embeds or iframes NemoClaw's control UI (`:8080`). SSE/websocket or JSONL tailing for live telemetry.
- **Models & serving (D):** DiffusionGemma `nvidia/diffusiongemma-26B-A4B-it-NVFP4` (~18 GB) + `google/gemma-4-26B-A4B-it` (AR baseline). Serving ladder: **NVIDIA NIM → vLLM `vllm/vllm-openai:gemma4` image → HF Transformers + NVFP4 behind a FastAPI shim** (the floor). Docker + NVIDIA Container Toolkit.
- **Staging status (June 14, 2026):** DiffusionGemma and Gemma 4 AR weight directories are already present on local disk under `/home/dell/factorymind/models/` and mirrored on the SSD under `/media/dell/T9/factorymind/models/`.
- **Hardware / OS:** GB10 (Grace Blackwell, 128 GB unified memory), aarch64 / DGX OS (Ubuntu-based).
- **Required-stack layer (on-brief):** NemoClaw — **the central agent harness, not optional**.

---

## 7. Key Decisions and Assumptions

**Decisions:**
- **NemoClaw is the agent harness** — not a bolt-on. The custom Python control loop is gone; NemoClaw calls B's tool server. This makes the required stack *central*, not optional, and directly answers the brief.
- **DiffusionGemma is the hero planner because it fits the hardware thesis,** not because it is a proven VLA yet. Phase 1 uses text + structured state; Phase 2 can test image/video only after the core endpoint is green. We pitch *"parallel generation for parallel control, fully local,"* never *"diffusion is fundamentally better."*
- **AR Gemma 4 is the primary fallback — the plan, not a panic button.** Same NemoClaw loop, same cell; we lose the diffusion speed story, not the project.
- **NVFP4 weights, not BF16** — smaller footprint, NVIDIA-optimized, matches the "~18 GB" framing.
- **Action blocks are deliberately long** (cell plan + per-robot reasoning) so diffusion's parallelism actually wins; diffusion has *higher* time-to-first-token so short outputs don't favour it.
- **Hard schema enforced at the tool boundary** — `step()` rejects bad `CellPlan`; NemoClaw reprompts once; then `hold_position` fires. The loop never blocks.
- **Three safety nets:** A's deterministic oracle policy, B's NemoClaw mock endpoint, C's replay mode — each still routes through NemoClaw for the demo.
- **No benchmark numbers we didn't measure on the box that day.**

**Assumptions (verify on the day):**
- NemoClaw is now installed (done); `nemoclaw onboard` still needs local-provider selection in a TTY.
- **Venue WiFi can't move 40–60 GB** → weights *and* Docker images travel on the SSD (`docker save` / `docker load`).
- A monitor is available (or the dashboard is served locally and opened in the box's browser — SSH X-forwarding is too laggy).
- The vLLM image with DiffusionGemma support needs the specific `:gemma4` tag rather than a stock `pip install vllm`.

---

## 8. Scope: Now vs. Future

**Current scope (ships today):**
- 2 robot arms, **one** assembly task, a single cell.
- **NemoClaw as the agent harness** — the required stack is the demo, not a checkbox.
- Local inference only; hard schema enforced at the tool boundary (`step` rejects bad `CellPlan`).
- Live diffusion-vs-AR latency dashboard with NemoClaw control UI embedded.
- Oracle-backed NemoClaw mock endpoint / replay fallbacks for a guaranteed demo.

**Future improvements (post-hackathon):**
- More arms and tasks; a real multi-station line.
- **Phase 2 VLA/video replanning** — camera frame or video in, perception identifies conditions such as "green box" or "part misaligned," then NemoClaw feeds the resulting object state into the same tool loop. This starts only after DiffusionGemma works on the box.
- **Memory and channels** via NemoClaw — persistent episode memory, Slack/email notifications on cell events.
- **Guided-decoding hardening** to eliminate structured-output parse failures under diffusion.
- A real, reproducible **benchmark suite** (so speed claims are measured, not framed).
- Production packaging via **NIM**, with NemoClaw kept as the only agent orchestration surface.

---

## 9. Role-Specific References

All four roles live in one detailed file today, each as its own section. Direct references:

- **Role A — Simulation Engineer** → [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md#role-a--simulation-engineer)
- **Role B — Agent Engineer** → [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md#role-b--agent-engineer-control-loop-schemas-mock-llm-telemetry)
- **Role C — Frontend Engineer** → [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md#role-c--frontend-engineer-diffusion-vs-ar-latency-dashboard)
- **Role D — Models & Box** → [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md#role-d--models--box-weights-serving-scripts-gb10-first-hour)
- **Shared Contracts (C1–C5)** and the **Integration & Demo** plan → same file, top and bottom sections.

> When you outgrow the single file, split into `roles/A_simulation.md`, `roles/B_agent.md`, `roles/C_frontend.md`, `roles/D_models_box.md` and repoint the links above. Keep the **Shared Contracts** in one place (here in the overview, or a dedicated `contracts.md`) so every role references one definition.

---

*This overview is the index and the why; the roles doc is the how. If a shared contract changes, update it there first — every role depends on those five.*