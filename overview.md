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

**Solution.** A single persistent agent runs the entire control loop **on the box** — local, always-on, and fast. It reads the cell state, asks a local model for the next coordinated action across all robots, validates the output against a hard schema, steps the cell, and repeats. No data leaves the device; no decision waits on the network.

**The on-theme insight.** DiffusionGemma generates a whole block of tokens *in parallel* per pass instead of one at a time. We frame each control decision as a structured block — all N robots' next moves in a single parallel generation pass. **Parallel generation for parallel control.** This is exactly the kind of single-user, low-latency local workload the GB10 exists to sell, and exactly what cloud inference is worst at.

---

## 2. Main Goal

Ship a working **always-on, fully-local multi-robot controller** and prove the thesis on stage: a live, side-by-side **diffusion-vs-autoregressive latency dashboard** where the diffusion-driven cell keeps moving while the AR baseline lags — running entirely on the GB10, with nothing going to the cloud.

The win condition for the judges (Dell + NVIDIA executives) is a demo that shows **why this specific local box matters** — on-prem data, low latency, and a capability the cloud structurally can't match.

> **North-star ship order:** (1) sim + loop with a mock model on a laptop → (2) same loop on the box with AR Gemma 4 → (3) latency dashboard → (4) DiffusionGemma hero path *if* 1–3 are green. There is always a working demo at each step.

---

## 3. The Four Roles (summary)

| Role | Owner of | In one line |
|---|---|---|
| **A — Simulation** | The cell | MuJoCo: 2 arms, one pick-and-place task, exposes `get_state()` / `step()` and a deterministic oracle policy. |
| **B — Agent** | The brain | The control loop, the JSON action schema, the model-agnostic `LLMClient` (mock / real / oracle), and telemetry. |
| **C — Frontend** | The proof | The local diffusion-vs-AR latency dashboard plus the cell visualization — the demo's persuasion surface. |
| **D — Models & Box** | Inference + hardware | Weights on SSD, local OpenAI-compatible serving, install scripts, and the GB10 first-hour bring-up. |

Full responsibilities, workflows, and failure handling for each are in [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md) (see §6 for direct links).

---

## 4. How the Roles Interact

Everything composes through **five frozen contracts** (defined in full in the roles doc, §"Shared Contracts"). Freeze these before anyone goes heads-down — they are why four people can build in parallel against mocks and merge cleanly.

- **C1 — Action schema** (`CellPlan`): the model's output and the only thing the sim accepts. *A + B co-own.*
- **C2 — Sim-state schema**: what `get_state()` returns and what B feeds the model. *A owns.*
- **C3 — `LLMClient` interface**: one interface, swappable backends (mock / OpenAI-compatible / oracle). *B owns.*
- **C4 — Endpoint contract**: `base_url`, model name, structured-output support, `max_model_len`. *D owns, hands to B.*
- **C5 — Telemetry JSONL**: one line per control step; the dashboard's only data source. *B owns, C consumes.*

```
   A (Sim) ──C2 state──▶ B (Agent) ──prompt──▶ D (Models): :8000 diffusion / :8001 AR
   A (Sim) ◀─C1 actions─ B (Agent) ◀─tokens───   ─────────────────────────────────
        │                     │ C5 telemetry JSONL
        └── frames ──────▶ C (Frontend) ◀── reads telemetry, renders the cell + latency race
   D (Box) ── C4 endpoints ─▶ B        D ── GL/EGL stack ─▶ A        D ── serve port ─▶ C
```

The dependency seams, in build order of risk: **A↔B** (closeable immediately via mock + smoke test) → **B↔C** (closeable via mock/replay, no GPU) → **D↔B** (the last and riskiest seam — so bring up AR Gemma 4 first to unblock everyone).

---

## 5. End-to-End Workflow

**Runtime control loop (the always-on agent):**

1. **Read** — B calls A's `get_state()` → current cell state (C2).
2. **Plan** — B prompts the local model (via C3 `LLMClient` → D's endpoint) for a `CellPlan` (C1): one coordinated action block for all robots.
3. **Parse + validate** — B enforces the schema hard; on failure, reprompt once; on a second failure, **hold position** (no-op) and log it. The loop never blocks.
4. **Step** — B passes the validated actions to A's `step()`; physics advances; events emit (pick success, collision, task complete).
5. **Log** — B writes one telemetry line (C5): latency, time-to-first-token, tokens, parse result, action summary, sim event.
6. **Render** — C reads the telemetry stream and A's frames, updating the dashboard live.
7. **Repeat** — continuously, always-on.

For the hero moment, steps 2–6 run twice over identical state — once against DiffusionGemma (`:8000`), once against AR Gemma 4 (`:8001`) — and the dashboard shows both clocks side by side.

**Build-time sequence:** follow the north-star ship order (§2). Laptop-green (mock + oracle + replay all working) **before** first contact with the box.

---

## 6. Architecture and Technology Stack

```
                    Dell Pro Max with GB10 (128 GB unified, aarch64 / DGX OS)
 ┌───────────────────────────────────────────────────────────────────────────┐
 │   MuJoCo cell (A)            Control loop (B)            Model serving (D)   │
 │   ┌──────────────┐  state    ┌──────────────┐  prompt   ┌────────────────┐  │
 │   │ 2 robot arms │──────────▶│ read→plan→   │──────────▶│ DiffusionGemma │  │
 │   │ parts, bins  │           │ parse→step→  │  /v1/chat │  :8000 (NVFP4)  │  │
 │   │ get_state()  │◀──────────│ log          │◀──────────│ Gemma 4 AR      │  │
 │   │ step()       │  actions  └──────┬───────┘  tokens   │  :8001          │  │
 │   └──────┬───────┘                  │ telemetry JSONL   └────────────────┘  │
 │          │ frames                   ▼                                        │
 │          └──────────────▶ Latency dashboard (C) ◀── browser on the box      │
 │                            diffusion vs AR, live                            │
 │                                                                             │
 │   Optional on-brief runtime layer: OpenClaw + NemoClaw + OpenShell           │
 └───────────────────────────────────────────────────────────────────────────┘
              No outbound internet during the demo — that's the point.
```

**Stack by layer:**

- **Simulation (A):** MuJoCo (`mujoco` Python bindings, MJCF scenes, offscreen/EGL rendering), NumPy. Fallback engine: PyBullet.
- **Agent (B):** Python, Pydantic v2, the `openai` client (OpenAI-compatible `/v1/chat/completions`), structured / guided-JSON decoding, `httpx` for latency measurement.
- **Frontend (C):** React/TypeScript + Vite + Tailwind + a charting lib for the polished build; a single static-HTML + vanilla-JS version as the robust fallback. SSE/websocket or JSONL tailing for live data.
- **Models & serving (D):** DiffusionGemma `nvidia/diffusiongemma-26B-A4B-it-NVFP4` (~18 GB) + `google/gemma-4-26B-A4B-it` (AR baseline). Serving ladder: **NVIDIA NIM → vLLM `vllm/vllm-openai:gemma4` image → HF Transformers + NVFP4 behind a FastAPI shim** (the floor). Docker + NVIDIA Container Toolkit.
- **Hardware / OS:** GB10 (Grace Blackwell, 128 GB unified memory), aarch64 / DGX OS (Ubuntu-based).
- **Required-stack layer (on-brief):** OpenClaw + NemoClaw + OpenShell — onboarded as the secure local runtime if time allows.

---

## 7. Key Decisions and Assumptions

**Decisions:**
- **DiffusionGemma is the hero because it fits the hardware thesis,** not because it's "better." It's built for single-user local inference where the GPU is otherwise idle — the GB10's exact value prop. We pitch *"parallel generation for parallel control, fully local,"* never *"diffusion is fundamentally better."*
- **AR Gemma 4 is the primary fallback — the plan, not a panic button.** Same loop, same cell; we lose the diffusion speed story, not the project.
- **NVFP4 weights, not BF16** — smaller footprint, NVIDIA-optimized, matches the "~18 GB" framing.
- **Action blocks are deliberately long** (cell plan + per-robot reasoning) so diffusion's parallelism actually wins; diffusion's advantage is on long outputs and it has *higher* time-to-first-token.
- **Hard schema, parse hard, retry once, then hold position.** Reliability over cleverness; the loop must never block.
- **Three safety nets built into the plan:** A's deterministic oracle policy, B's mock client, C's replay mode — each is a working worst-case demo.
- **No benchmark numbers we didn't measure on the box that day.** Public framing: *"~1.9× tokens/sec, ~3.3× faster end-to-end on longer outputs,"* with time-to-first-token reported separately.

**Assumptions (verify on the day):**
- We have **no GB10 access before the event** → first contact = a 60–90 min bring-up hour. Hence the laptop-green-before-box rule and D's serving ladder.
- Organizers pre-stage OpenClaw + NemoClaw + OpenShell; the box is aarch64 / DGX OS with Ollama present.
- **Venue WiFi can't move 40–60 GB** → weights *and* Docker images travel on the SSD (`docker save` / `docker load`).
- A monitor is available (or the dashboard is served locally and opened in the box's browser — SSH X-forwarding is too laggy).
- The vLLM image with DiffusionGemma support may need the specific `:gemma4` tag rather than a stock `pip install vllm`.

> **Honest fit note:** the brief asks for a *business agent* on the OpenClaw + NemoClaw + OpenShell + Nemotron stack. FactoryMind frames manufacturing-cell control as the business use case and treats the required stack as the secure local runtime. Making an OpenClaw/Nemotron supervisory agent the *explicit* business layer is a tracked future improvement (§8), not part of the day-one demo.

---

## 8. Scope: Now vs. Future

**Current scope (ships today):**
- 2 robot arms, **one** assembly task, a single cell.
- Local inference only; structured-JSON control loop with hard validation.
- Live diffusion-vs-AR latency dashboard.
- Oracle / mock / replay fallbacks for a guaranteed demo.

**Future improvements (post-hackathon):**
- More arms and tasks; a real multi-station line.
- True **multimodal replanning** — camera frame in ("bin empty," "part misaligned") → the agent replans.
- An **OpenClaw + Nemotron supervisory agent** as the explicit always-on business layer, with DiffusionGemma as the fast local executor (closes the brief-fit gap and adds memory/channels/tools).
- **Guided-decoding hardening** to eliminate structured-output parse failures under diffusion.
- A real, reproducible **benchmark suite** (so speed claims are measured, not framed).
- Production packaging via **NIM**, and security/guardrails via **OpenShell** (network/filesystem isolation, credential separation).

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