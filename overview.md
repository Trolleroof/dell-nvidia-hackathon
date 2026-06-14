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

Ship a working **always-on, fully-local multi-robot controller** and prove the thesis on stage: a **diffusion-vs-autoregressive latency dashboard** where each model is measured **in isolation** on the GB10, then **replayed side-by-side** so judges see diffusion finish each action block faster than AR — with nothing going to the cloud.

The win condition for the judges (Dell + NVIDIA executives) is a demo that shows **why this specific local box matters** — on-prem data, low latency, and a capability the cloud structurally can't match. This is a **relative** race (diffusion faster than AR on the same task), not a claim of absolute real-time control — expect roughly **1–2 decisions/sec** on a bandwidth-limited GB10, not 30 Hz.

> **North-star ship order:** (1) sim + NemoClaw loop with a mock endpoint on a laptop → (2) same loop on the box with AR Gemma 4 → (3) latency dashboard → (4) DiffusionGemma hero path *if* 1–3 are green → (5) Phase 2 VLA/video perception only if everything else is already working. There is always a working demo at each step.

---

## 3. The Four Roles (summary)

| Role | Owner of | In one line |
|---|---|---|
| **A — Simulation** | The cell | MuJoCo: 2 arms, one pick-and-place task, exposes `get_state()` / `step()` as NemoClaw tools and a deterministic oracle policy. |
| **B — Agent** | Control loop + schema | Owns the Python control loop (`get_state` → plan → `step`), action schema (C1), telemetry (C5), and tool server; records isolated per-model runs for replay. |
| **C — Frontend** | The proof | Diffusion-vs-AR dashboard via **replay of two isolated runs** side-by-side; wall-clock per action block as headline; optional NemoClaw UI embed. |
| **D — Models & Box** | Inference + hardware | Weights on SSD, local OpenAI-compatible serving, NemoClaw bring-up, install scripts, and the GB10 first-hour gate. |

Full responsibilities, workflows, and failure handling for each are in [`FactoryMind_Team_Roles.md`](FactoryMind_Team_Roles.md) (see §6 for direct links).

---

## 4. How the Roles Interact

Everything composes through **five frozen contracts** (defined in full in the roles doc, §"Shared Contracts"). Freeze these before anyone goes heads-down — they are why four people can build in parallel against mocks and merge cleanly.

- **C1 — Action schema** (`CellPlan`): the model's output and the only thing the sim accepts. *A + B co-own.*
- **C2 — Sim-state schema**: what `get_state()` returns; exposed as the `get_state` NemoClaw tool payload. Phase 1 includes ground-truth object attributes such as id, color, position, and location so text tasks like "sort green boxes" do not require camera perception. *A owns.*
- **C3 — NemoClaw tool definitions**: the three tools NemoClaw calls (`get_state`, `step`, `hold_position`), their JSON schemas, and the tool server port. *B owns; configured only through NemoClaw profiles.*
- **C4 — Endpoint contract**: `base_url`, model name, structured-output support, `max_model_len`. *D owns, hands to B (and NemoClaw config).*
- **C5 — Telemetry JSONL**: one line per control step; **one full run per model** for replay. Headline field: `latency_ms` (wall-clock per valid action block). *B owns, C consumes.*

```
   A (Sim) ◀──────────────────────────────────────────────────────────────┐
   get_state / step / hold_position (C3, served by B)                     │
        │                                                                  │
        ▼                                                                  │
   B control loop (Python) ──one model at a time──▶ D (Models)
        │  text task + C2 state; validate CellPlan     :8000 *or* :8001
        │  (not concurrent — same GPU contends)          diffusion *or* AR
        │ C5 telemetry JSONL (one run per model)
        ▼
   C (Frontend): replay two recorded runs side-by-side + optional live single-model feed
        headline metric: wall-clock ms per valid action block
   D (Box) ── C4 endpoints ─▶ B config          D ── GL/EGL stack ─▶ A
```

**Latency race rule:** do **not** call DiffusionGemma and AR in parallel on one GB10 — they contend for the same SMs and memory bandwidth, so a live concurrent race measures contention, not architecture. Run the full scenario on diffusion, record C5; run it again on AR at **matched precision**, record C5; let C's **replay mode** play both traces next to each other. Fair, crash-proof, and the dashboard already has the replay path.

**Brief-fit note:** NemoClaw is the on-brief harness target, but the latency-comparison data path is B's plain Python loop hitting model endpoints — not a live dual-NemoClaw race. NemoClaw UI (`:8080`) can still be embedded for the agent story; the measured clocks come from B's isolated runs.

The dependency seams, in build order of risk: **A-B** (closeable through mock endpoint + smoke test) -> **B-C** (closeable via recorded telemetry replay, no GPU) -> **D-B** (the last and riskiest seam — bring up AR Gemma 4 first, one model loaded at a time).

---

## 5. End-to-End Workflow

**Runtime control loop (B's Python loop — NemoClaw is the on-brief harness target, but this is the measured data path):**

1. **Read** — B calls `get_state()` on A's sim → current cell state (C2), including object ids/colors/positions for Phase 1 sorting tasks.
2. **Plan** — B prompts the **single loaded model** (D's endpoint, C4) with the user text task, structured state, and schema; model returns a `CellPlan` (C1).
3. **Parse + validate** — B enforces the schema; on bad output, reprompt once; on a second failure, `hold_position`. The loop never blocks.
4. **Step** — B calls A's `step()` with the validated `CellPlan`; physics advances; events emit (pick success, collision, task complete).
5. **Log** — B emits one C5 JSONL line per step. **Headline field: `latency_ms`** = end-to-end wall-clock to produce one valid action block (the directly comparable metric — also what "keeps the line moving" means). Keep `ttft_ms`, `prompt_tokens`, and `completion_tokens` as secondary color only; they are not apples-to-apples across diffusion vs AR.
6. **Render** — C reads recorded telemetry and A's frames; optional NemoClaw control UI (`:8080`) embedded alongside.
7. **Repeat** — B keeps the loop running against whichever model is currently loaded.

**Hero moment (isolated measurement + replay, not a live concurrent race):**

1. Load **DiffusionGemma** at matched precision → run the full pick-and-place scenario → write `telemetry/diffusion_run.jsonl`.
2. Unload diffusion, load **AR Gemma 4** at the **same precision** (both NVFP4 ideal on GB10; both BF16 if NVFP4 AR isn't ready) → same scenario, same seed → write `telemetry/ar_run.jsonl`.
3. C's dashboard **replays both traces side-by-side** — wall-clock per action block as the headline number, diffusion finishing blocks faster than AR.

**Build-time sequence:** follow the north-star ship order (§2). Laptop-green (mock endpoint + oracle-backed sim + replay all working) **before** first contact with the box.

---

## 6. Architecture and Technology Stack

```
                    Dell Pro Max with GB10 (128 GB unified, aarch64 / DGX OS)
 ┌───────────────────────────────────────────────────────────────────────────┐
 │  MuJoCo cell (A)      B control loop + C2 state (B)    Models (D)         │
 │  ┌─────────────┐      ┌──────────────────────────┐  one at a time:         │
 │  │ 2 robot arms│◀────▶│ get_state → plan → step │─────▶ :8000 diffusion  │
 │  │ parts, bins │      │ validate CellPlan (C1)  │  *or* :8001 AR          │
 │  │ get_state() │      │ Python loop (not dual)  │◀────  matched precision │
 │  │ step()      │      └────────────┬────────────┘      (NVFP4↔NVFP4 or   │
 │  └──────┬──────┘                   │ C5 JSONL per run   BF16↔BF16)       │
 │         │ frames                   ▼                                        │
 │         │              telemetry/diffusion_run.jsonl                        │
 │         │              telemetry/ar_run.jsonl                               │
 │         ▼                          │                                        │
 │  C (Frontend): replay both runs side-by-side — wall-clock/action headline  │
 │                ~1–2 decisions/sec; optional NemoClaw UI (:8080) for story  │
 └───────────────────────────────────────────────────────────────────────────┘
              No outbound internet during the demo — that's the point.
```

**Stack by layer:**

- **Simulation (A):** MuJoCo (`mujoco` Python bindings, MJCF scenes, offscreen/EGL rendering), NumPy. Phase 1 exposes ground-truth object state, including color labels for sorting tasks; fallback engine: PyBullet.
- **Agent harness (NemoClaw — on-brief target):** NemoClaw is the required-stack story for judges; the **measured latency path** is B's Python control loop calling model endpoints directly. NemoClaw can still be shown via `:8080` embed, but do not route the latency race through dual live NemoClaw sessions.
- **Control loop + tool server (B):** Python + FastAPI + Pydantic v2. Owns the control loop: `get_state` → C2, `step(CellPlan)` → sim advance, `hold_position` → safety. Records C5 JSONL with **wall-clock `latency_ms` per valid action block** as the headline metric.
- **Frontend (C):** React/TypeScript + Vite + Tailwind + charting lib for the polished build; static-HTML + vanilla-JS fallback. **Replay mode is the hero path** for the diffusion-vs-AR comparison — plays two isolated recorded runs side-by-side. Optional live single-model feed; optional NemoClaw UI iframe.
- **Models & serving (D):** DiffusionGemma `nvidia/diffusiongemma-26B-A4B-it-NVFP4` (~18 GB) + `google/gemma-4-26B-A4B-it` (AR baseline). **Load one model at a time** — NVFP4 diffusion (~18 GB) + BF16 AR (~52 GB) plus KV cache, sim, rendering, and Docker on 128 GB unified is tight, not roomy. **Match precision** for a fair race: both NVFP4 (ideal on Blackwell) or both BF16; never NVFP4 diffusion vs BF16 AR without disclosing the gap out loud. Serving ladder: **NVIDIA NIM → vLLM `vllm/vllm-openai:gemma4` image → HF Transformers + NVFP4 behind a FastAPI shim** (the floor). Docker + NVIDIA Container Toolkit.
- **Staging status (June 14, 2026):** DiffusionGemma and Gemma 4 AR weight directories are already present on local disk under `/home/dell/factorymind/models/` and mirrored on the SSD under `/media/dell/T9/factorymind/models/`.
- **Hardware / OS:** GB10 (Grace Blackwell, 128 GB unified memory), aarch64 / DGX OS (Ubuntu-based).
- **Required-stack layer (on-brief):** NemoClaw — **the central agent harness, not optional**.

---

## 7. Key Decisions and Assumptions

**Decisions:**
- **Isolated measurement + replay, not a live concurrent race.** One model loaded at a time on the GB10; run the full scenario per model; C replays both C5 traces side-by-side. Parallel GPU calls would measure contention, not architecture.
- **Matched precision for a fair comparison.** Blackwell has hardware FP4, so NVFP4 DiffusionGemma vs BF16 AR exaggerates the win (a chunk of speedup is quantization, not diffusion). Race both at NVFP4, or both at BF16, or disclose the precision gap explicitly on stage.
- **Wall-clock per valid action block is the headline metric.** `latency_ms` = time from state-in to parsed `CellPlan` out. TTFT and tokens/sec are secondary — they mean different things for block-diffusion (whole 256-token canvas in a few denoising passes) vs autoregressive token streaming.
- **One model at a time for memory.** 128 GB unified is enough, but not roomy with two large models + KV cache + sim + Docker. Sequential loading sidesteps OOM and makes the isolated-measurement story natural.
- **Relative race, not real-time.** The GB10 is bandwidth-limited (~20 tok/s territory on large models). Expect ~1–2 control decisions/sec on a slow pick-and-place — honest framing, not 30 Hz.
- **NemoClaw is the on-brief harness target,** but B's plain Python loop is the measured data path for the latency comparison. NemoClaw UI can still be embedded for the agent story.
- **DiffusionGemma is the hero planner because it fits the hardware thesis,** not because it is a proven VLA yet. Phase 1 uses text + structured state; Phase 2 can test image/video only after the core endpoint is green. We pitch *"parallel generation for parallel control, fully local,"* never *"diffusion is fundamentally better."*
- **AR Gemma 4 is the primary fallback — the plan, not a panic button.** Same loop, same cell; we lose the diffusion speed story, not the project.
- **Action blocks are deliberately long** (cell plan + per-robot reasoning) so diffusion's parallelism actually wins on wall-clock; short outputs don't favour diffusion.
- **Hard schema enforced at the tool boundary** — `step()` rejects bad `CellPlan`; reprompt once; then `hold_position`. The loop never blocks.
- **Three safety nets:** A's deterministic oracle policy, B's mock endpoint, C's replay mode.
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
- Diffusion-vs-AR latency dashboard via **isolated runs replayed side-by-side** (wall-clock per action block headline); optional NemoClaw control UI embedded.
- Oracle-backed mock endpoint / recorded-telemetry replay fallbacks for a guaranteed demo.

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