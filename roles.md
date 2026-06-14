# FactoryMind — Team Roles & Responsibilities

**Project:** FactoryMind — an always-on, fully-local controller agent for a multi-robot assembly cell, powered by DiffusionGemma on the Dell Pro Max with GB10.
**Event:** Dell × NVIDIA "Local AI on Dell Pro Max with GB10" hackathon · June 14, 2026 · build window 10:00 → 18:00.
**One-line thesis:** A factory floor can't send data to the cloud and can't tolerate latency, so the controller runs local, always-on, and fast — one persistent agent coordinating a cell of robot arms, replanning in real time, entirely on the box.

> **North-star ship order (do not reorder):**
> 1. Sim tool server + NemoClaw agent with **mock endpoint** (runs on any laptop, zero GPU).
> 2. Same NemoClaw loop on the box with **AR Gemma 4** pointed at `:8001`.
> 3. Side-by-side **diffusion-vs-AR latency dashboard** with NemoClaw control UI embedded.
> 4. **DiffusionGemma** hero path on `:8000`, *if* steps 1–3 are green.
> 5. **Phase 2 VLA/video perception**, only after DiffusionGemma is actually working on the box.
>
> Every role's "done" is defined against this order. We always have a working demo at each step.

---

## Shared Contracts (read this first — these are why we can work in parallel)

Four people cannot move fast unless the seams between them are frozen early. Agree these **before** anyone goes heads-down. They are deliberately small.

### C1 — Action schema (owned jointly by A + B)
The model's output, and the only thing the sim accepts. Pydantic v2.

```python
class RobotCommand(BaseModel):
    id: int                       # robot index, 0..N-1
    action: Literal["move", "grip", "release", "hold"]
    target: str                   # named target, e.g. "bin_a", "station_1", "part_3"
    reason: str = ""              # short rationale (see note)

class CellPlan(BaseModel):
    plan: str                     # one-line cell-level intent
    robots: list[RobotCommand]    # one entry per robot
```

> **Why `reason` + `plan` exist (this is a correction, not decoration):** DiffusionGemma's speed advantage is on **long** outputs — it denoises a 256-token canvas in a few passes, and it has *higher* time-to-first-token than autoregressive. A two-robot block of bare JSON is short enough that AR can match or beat it. Pad the structured output with real content (`plan` + per-robot `reason`) so the generated block is long enough that parallel generation visibly wins. Keep it parseable, but make it substantial.

### C2 — Sim state schema (owned by A, consumed by B)
JSON-serializable. What `get_state()` returns and what B feeds the model. Phase 1 uses ground-truth sim state, not camera perception; include object attributes so text tasks like "sort green boxes" are possible.

```json
{
  "step": 42,
  "robots": [{"id": 0, "pose": "...", "gripper": "open|closed", "holding": "part_3|null"}],
  "task": "sort green boxes to station_1",
  "parts":  [{"id": "box_3", "color": "green", "pos": [0,0,0], "at": "bin_a|station_1|gripper_0|..."}],
  "stations": [{"id": "station_1", "status": "empty|occupied|done"}],
  "events": ["pick_success", "collision", "task_complete"],
  "done": false
}
```

### C3 — NemoClaw tool definitions (owned by B)
B runs a FastAPI tool server that NemoClaw calls. Three tools, each with a JSON schema NemoClaw receives at agent start:

```python
# Tool: get_state — no args, returns C2 state JSON
# Tool: step — args: CellPlan (C1 schema), returns {"ok": true, "events": [...]}
# Tool: hold_position — no args, no-op safety fallback, returns {"ok": true}

# On laptop dev: NemoClaw runs against a mock endpoint and the same tool server — no GPU required
# On box: same tool server, NemoClaw points at it; swap model endpoint via env var
```

There is no separate Python model client in the plan - NemoClaw owns every model call, and B only owns the tools it exposes.

### C4 — Endpoint contract (owned by D, handed to B)
What D must publish for B to point at:
`{ base_url, model_name, structured_output: bool, tool_call_parser, max_model_len }`
Fixed ports: **`DIFFUSION_URL=http://localhost:8000/v1`**, **`AR_URL=http://localhost:8001/v1`**.

### C5 — Telemetry JSONL schema (owned by B, consumed by C)
One line per control step. This is the dashboard's only data source.

```json
{"ts": 0.0, "step": 42, "model": "diffusiongemma|gemma4|mock|oracle",
 "endpoint": "http://localhost:8000/v1", "latency_ms": 0, "ttft_ms": 0,
 "prompt_tokens": 0, "completion_tokens": 0, "parsed_ok": true, "retries": 0,
 "action_summary": "r0 move bin_a; r1 grip part_3", "sim_event": "pick_success"}
```

### Repo layout (shared)
```
factorymind/
├── factorymind/
│   ├── sim/
│   │   └── a/          # A: Role A workspace — cell, oracle, MCP, assets (edit here only)
│   ├── tools/          # B:  FastAPI tool server (get_state/step/hold_position), schemas (C1/C2), telemetry extractor
│   └── demo/           # C:  dashboard (static-HTML + Vite), replay mode, NemoClaw UI embed
├── nemoclaw/           # B+D: nemoclaw agent config / NemoClaw system prompt / tool manifest
├── scripts/            # D:  box_setup.sh, start_models.sh, run_demo.sh, save_images.sh
├── models/             # D:  (gitignored) NVFP4 diffusion + AR weights, copied from SSD
├── telemetry/          # B→C runtime JSONL (extracted from NemoClaw logs)
├── CODEOWNERS.md       # who owns which folder (avoid merge conflicts)
├── requirements.txt    # pinned; pip install ON THE BOX (no Mac wheels)
└── README.md
```

Role A integration for B: `from factorymind.sim.a import create_cell_env`

---

## Role A — Simulation Engineer

### Purpose
Own the physical world the agent controls. Provide a clean, deterministic `get_state()` / `step()` interface that hides all physics from the rest of the team, so B can drive it and C can show it without ever touching MuJoCo.

### Main responsibilities
- Author the MuJoCo cell: **2 robot arms** (use existing models — MuJoCo Menagerie / robosuite — do **not** build arms from scratch), a table, parts, and bins/stations, doing **one** task (pick-and-place / sort / stack).
- Implement `reset(seed)`, `get_state()` (returns C2), and `step(actions: CellPlan)` (apply per-robot commands, advance physics, return new state + events). C2 must include object ids, colors, positions, and locations for Phase 1 text tasks like "sort green boxes."
- Map high-level named targets (`"bin_a"`, `"station_1"`) to actuator/joint goals via a **precomputed lookup table of poses** — avoid live inverse kinematics under time pressure.
- Provide a deterministic **oracle policy** (scripted correct actions) so the loop and dashboard work with no model at all.
- Offscreen-render a frame for the dashboard. Camera/video/VLA is Phase 2 only; Phase 1 should work from structured sim state.

### Required tools, skills, technologies
MuJoCo (`mujoco` Python bindings: `MjModel`, `MjData`, `mj_step`, `Renderer`), MJCF/XML scene authoring, offscreen/EGL headless rendering, NumPy, basic robotics intuition. **Fallback engine:** PyBullet if MuJoCo headless GL on aarch64/DGX OS misbehaves.

### Inputs and expected outputs
- **Inputs:** parsed `CellPlan` from B; config (task params, seed, N arms).
- **Outputs:** C2 state object (to B), including object color/location metadata; rendered frames (to C); episode events. All JSON-serializable.

### Step-by-step workflow
1. Stand up the MJCF scene with 2 arms + parts; confirm it loads and renders.
2. Define and freeze the C2 state schema with B.
3. Implement `reset` / `get_state` / `step`; clamp out-of-range targets.
4. Build the named-target → pose lookup table.
5. Write the **oracle policy** and a `smoke_test` (`python -m factorymind.sim.a.smoke_test`): arms complete the task end-to-end with no LLM.
6. Add offscreen render → PNG/np frame for C; expose structured scenarios such as "green boxes in bin_a" for Phase 1 sorting. Save camera/video perception for Phase 2.
7. Hand C1 (with B) and C2 over; keep the interface stable.

### Collaboration
- **With B:** co-own the action schema (C1); B calls your `get_state()` / `step()`. Your oracle policy is B's third "client" and the worst-case demo.
- **With C:** supply frames (or, if rendering fails, agree that C can run numbers-only).
- **With D:** your sim must run on the box — flag headless GL/EGL early so D installs the right GL stack.

### Edge cases, limitations, failure handling
- Invalid/unsafe action → clamp or no-op + emit a flag event.
- Collision → detect contact, log `collision` event, hold/reset the offending arm.
- Physics NaN / blow-up → reset the episode, log it.
- Gripper misses → treat as failed pick, allow retry/hold.
- Non-determinism → fix the seed; the latency race must compare identical scenarios.
- Headless render fails → degrade to state-only telemetry (dashboard shows numbers, no video). This is acceptable for Phase 1 because planning uses structured state, not pixels.

### Suggested improvements / missing details
- Parameterize for N arms but **ship with 2**; only add the 3rd if everything is green by 15:00.
- Reuse a robosuite pick-and-place task rather than authoring physics.
- Precompute poses; no live IK.
- The oracle policy is the highest-leverage safety net you can build — do it early.

---

## Role B — Tool Server Engineer (NemoClaw Tools, Schemas, Telemetry)

### Purpose
Own the interface between NemoClaw and the physical sim. Build and serve the three tools NemoClaw calls. Own the action schema (C1), the tool definitions (C3), and telemetry extraction (C5). **You do not build or own the control loop — NemoClaw is the loop.**

### Main responsibilities
- Define and own C1 (action schema), C3 (tool definitions), C5 (telemetry).
- Run a **FastAPI tool server** that exposes `get_state`, `step`, and `hold_position` as HTTP endpoints with JSON schemas NemoClaw can consume.
- `step()` validates the incoming `CellPlan` (Pydantic v2) hard; returns `{"ok": false, "error": "..."}` on schema violation so NemoClaw reprompts; on a second bad call within the same step, call `hold_position` internally.
- Write and maintain the **NemoClaw system prompt** (`nemoclaw/system_prompt.md`): task description, tool manifest, 1–2 golden examples, schema instructions, and examples like "sort green boxes" from structured state. This is the prompt engineering work.
- **Telemetry extractor:** tail NemoClaw's agent log (JSONL), parse tool-call timings and model latency, emit one C5 line per sim step.
- **Mock mode:** NemoClaw points at a local mock endpoint while the tool server runs against A's oracle-backed sim for laptop dev and CI.

### Required tools, skills, technologies
Python, FastAPI, Pydantic v2, `uvicorn`, prompt engineering (the system prompt is now the place for it), log parsing. Optionally `httpx` for the telemetry extractor.

### Inputs and expected outputs
- **Inputs:** tool calls from NemoClaw (JSON over HTTP); user text task; C2 state from A's sim with object attributes; C4 endpoint info from D (needed to write the NemoClaw agent config, not to make the model call yourself).
- **Outputs:** tool responses → NemoClaw; C5 telemetry JSONL → C's dashboard.

### Step-by-step workflow
1. Define C1 + write two golden example tool call/response pairs.
2. Stand up the FastAPI tool server for NemoClaw mock/oracle mode; smoke test: `POST /step` with a valid `CellPlan`, confirm sim advances.
3. Write `nemoclaw/agent_config.yaml` (or equivalent NemoClaw config): tool server URL, model endpoint (C4), system prompt path.
4. Launch NemoClaw pointed at the tool server + mock endpoint; confirm NemoClaw completes one full pick-and-place episode.
5. Write the telemetry extractor; confirm C5 JSONL appears in `telemetry/`.
6. On the box: update `agent_config.yaml` with `AR_URL=http://localhost:8001/v1`; NemoClaw drives the real model.
7. For the race: two NemoClaw instances, one per model endpoint, over identical state; telemetry extractor logs both.

### Collaboration
- **With A:** co-own C1; your `step` tool wraps A's `step()`; the oracle mode is your mock path.
- **With D:** C4 endpoint info goes into `agent_config.yaml` — D hands you the URL and model name; you write the config.
- **With C:** freeze C5 fields and the JSONL path/transport up front; C builds against it immediately.

### Edge cases, limitations, failure handling
- NemoClaw sends bad `CellPlan` → `step` tool returns `{"ok": false}` → NemoClaw reprompts → second failure → tool server calls `hold_position`; loop never blocks.
- Tool server crash → NemoClaw stalls; keep the tool server simple, restart-safe, and log exceptions.
- **Diffusion structured-output reliability** → the tool schema is the hard constraint; prefer guided-JSON/tool-calling on the vLLM side (D's config).
- Telemetry extractor can't parse a NemoClaw log format → emit a partial C5 line with `parsed_ok=false`; dashboard degrades gracefully.

### Suggested improvements / missing details
- Keep the system prompt short and the tool schemas tight — diffusion canvas is 256 tokens; the system prompt eats into that.
- Log enough to compute mean/p50/p95 latency and parse-success rate for the pitch.
- Add a "replan on event" tool response path (`{"ok": true, "replan": true, "reason": "bin empty"}`) for structured-state replanning. Camera/video/VLA belongs to Phase 2 after DiffusionGemma is live.

---

## Role C — Frontend Engineer (Latency Dashboard + NemoClaw UI Integration)

### Purpose
Own the visible proof. Build the local dashboard that makes the latency argument something judges *see*, plus the cell visualization. **Also integrate NemoClaw's own control UI (`:8080`) into the demo surface** — embed it in an iframe or link to it prominently so judges can see the agent thinking in real time alongside the latency race.

### Main responsibilities
- Build a dashboard that **runs on the box and opens in the box's browser** (never SSH X-forwarding — it's laggy).
- Show: (1) the cell (A's frames, or a clean viz), (2) the active text task and parsed object targets (for example green boxes), (3) **side-by-side latency panels** — tokens/sec, TTFT, total ms, throughput-over-time, (4) the parsed action/tool-call stream, (5) an aggregate stats panel, (6) **NemoClaw control UI embedded** (iframe pointing at `http://localhost:8080`).
- Consume C5 telemetry (live feed from B's extractor, or tail the JSONL).
- Make every number legible from across a room; show a clear "winner" indicator — honestly.
- Rehearse the whole narrative on a laptop with **mock fast/slow timings** before the box exists.

### Required tools, skills, technologies
React/TypeScript + Vite + Tailwind + a charting lib (Recharts/Chart.js) for the polished version. **Critical decision up front:** also build a **single static HTML + vanilla-JS** version — far more robust to serve on an unfamiliar box. SSE/websocket or polling for the live feed; `<img>`/canvas for frames; `<iframe src="http://localhost:8080">` for NemoClaw UI.

### Inputs and expected outputs
- **Inputs:** C5 telemetry from B's extractor (fields + transport agreed up front); frames or state from A; NemoClaw control UI at `:8080`.
- **Outputs:** the dashboard on the projector with NemoClaw UI visible; a clean screen recording + screenshots as the fallback artifact.

### Step-by-step workflow
1. Freeze C5 fields and transport with B.
2. Build the layout (cell view | NemoClaw UI iframe | dual latency panels | action/tool-call stream | stats) against **mock** fast/slow data — rehearse the story with no GPU.
3. Wire to B's live telemetry feed; add a **replay mode** that plays a recorded JSONL.
4. Add the winner visual; show TTFT vs total honestly.
5. Make it room-legible (huge fonts, high contrast).
6. On the box: point at real endpoints, set iframe src to `http://localhost:8080`, serve locally, confirm it opens in the box browser.
7. Capture a clean recording as the worst-case demo.

### Collaboration
- **With B:** total dependency on C5 — agree it first, build against mock data immediately. Also coordinate the tool-call stream format so the action panel shows NemoClaw tool calls, not raw JSON.
- **With A:** render frames, or fall back to numbers-only if rendering is down.
- **With D:** coordinate the serve port, NemoClaw UI port (`:8080`), and that everything opens in the box browser; ship the static-HTML fallback if Vite fights the box.

### Edge cases, limitations, failure handling
- NemoClaw UI not yet running → show a placeholder panel with "NemoClaw starting..." rather than a broken iframe.
- No live telemetry yet → mock/replay mode (also the worst-case demo).
- Frames fail (headless render broken) → numbers-only latency race (still compelling).
- **Diffusion does NOT visibly win for short outputs** → rely on B's long action blocks, report TTFT vs total honestly.
- Projector/browser issues → screenshot deck + recording.
- Full Vite build fails on box → static-HTML fallback.

### Suggested improvements / missing details
- Build the static-HTML fallback **in parallel** with the Vite app, not after.
- Replay mode decouples you from a live box and *is* the worst-case demo — high priority.
- Add a "cloud (simulated, with network delay)" toggle to dramatize the on-prem/latency thesis.
- If NemoClaw's control UI supports theming or embedding params, use them to match the dashboard's visual language.

---

## NIKHIL PRABHU - Role D — Models & Box (Weights, Serving, Scripts, GB10 First Hour)

### Purpose
Own inference and the hardware. Get both models served locally on the GB10 behind OpenAI-compatible endpoints, own the first-hour bring-up, own every install script, and gate the team. **Most time-critical and highest-risk role — start at minute zero, staff it with the strongest infra person.**

### Main responsibilities
- Stage weights on SSD at home; copy to the box's internal NVMe day-of.
- Stand up serving with a **fallback ladder**, exposing `:8000` (diffusion) and `:8001` (AR).
- Own `scripts/box_setup.sh`, `start_models.sh`, `run_demo.sh`, and `save_images.sh`.
- Run the GB10 first-hour runbook and enforce the gate: **no feature work on the box until `curl localhost:8001/v1/models` succeeds.**
- Hand C4 (endpoints) to B; communicate clearly which models are actually up. Do not spend core build time on video input until AR, NemoClaw, dashboard, and DiffusionGemma are green.
- (On-brief, time permitting) onboard NemoClaw so the "required stack" box is checked.

### Required tools, skills, technologies
vLLM via the **`vllm/vllm-openai:gemma4` Docker image** (stock `pip install vllm` likely lacks DiffusionGemma support — it's days old); **NVIDIA NIM** (containerized DiffusionGemma microservice, the easiest one-command path on NVIDIA HW); **HF Transformers + NVFP4** wrapped in a tiny FastAPI `/v1/chat/completions` shim (the floor — runs on DGX Spark out of the box); Docker + NVIDIA Container Toolkit; `rsync`/`lsblk`/`mount`; systemd; bash; ARM64/DGX OS; `hf download`.

**Weights (download at home):**
- Hero: **`nvidia/diffusiongemma-26B-A4B-it-NVFP4`** (~13–18 GB, NVFP4, NVIDIA-optimized) — use this, *not* the larger BF16 `google/diffusiongemma-26B-A4B-it`.
- Baseline: **`google/gemma-4-26B-A4B-it`** (AR, same MoE family). On 128 GB unified, NVFP4 diffusion (~18 GB) + BF16 AR (~52 GB) fits with headroom; use an NVFP4 AR variant if you want a lighter, fairer pair.

### Inputs and expected outputs
- **Inputs:** SSD with weights + scripts + saved Docker images + `nemoclaw.sh`; the GB10 (first contact day-of); organizer answers (is NemoClaw pre-installed? is there a monitor? SSH host?).
- **Current staging status (June 14, 2026):** both model payloads are already staged locally at `/home/dell/factorymind/models/` and on the SSD at `/media/dell/T9/factorymind/models/`, with DiffusionGemma as the intended primary inference payload.
- **Outputs:** two live OpenAI-compatible endpoints + their C4 info to B; a documented, repeatable bring-up; the demo machine ready.

### Step-by-step workflow
0. Confirm the box: `uname -m` (must be `aarch64`), `nvidia-smi`, `docker info`.
1. Mount SSD (`lsblk` → `sudo mount` or auto `/media/$USER/`); `rsync -ah --info=progress2` weights → `~/factorymind/models/`, repo → `~/factorymind/`. **Do not copy Mac wheels** — `pip install -r requirements.txt` on the box.
2. **Bring up AR Gemma 4 first** on `:8001` (the known path); `curl localhost:8001/v1/models` must pass before anything else. Unblock B/C immediately.
3. Bring up DiffusionGemma on `:8000` by the ladder: **NIM container → vLLM `:gemma4` image → HF Transformers + NVFP4 FastAPI shim.** vLLM flags: `VLLM_USE_V2_MODEL_RUNNER=1 vllm serve ... --trust-remote-code --attention-backend TRITON_ATTN --enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4 --hf-overrides '{"diffusion_sampler":"entropy_bound","diffusion_entropy_bound":0.1}' --diffusion-config '{"canvas_length":256}' --enable-chunked-prefill`.
4. Hand C4 to B.
5. **Hard stop:** if diffusion isn't up by ~12:00, stop debugging it — lock the AR-only demo + architecture story. The fallback is the plan, not a panic.
6. Own the demo machine: monitor plugged in, ports open, dashboard served locally.

### Collaboration
- **With B:** C4 is the handoff — URL, model name, structured-output/tool-calling support, `max_model_len`. Tell B exactly what's live (diffusion? AR? both?) so B/C pick the demo narrative.
- **With C:** coordinate serve port + box browser.
- **With A:** install the GL/EGL stack the sim needs headless.
- **With everyone:** your first-hour gate unblocks the team — communicate status loudly.

### Edge cases, limitations, failure handling
- **vLLM image not yet on a stable release / pip lacks support** → use the `vllm/vllm-openai:gemma4` Docker tag or NIM; HF Transformers + NVFP4 is the floor.
- **Venue WiFi can't pull multi-GB image layers** → at home, `docker save vllm/vllm-openai:gemma4 -o image.tar` (and the NIM container) onto the SSD; `docker load` on the box. *(Weights on the SSD are not enough — the runtime image matters just as much.)*
- `TRITON_ATTN` / attention-backend errors → it's a vLLM/CUDA/Triton/arch mismatch; fix the **stack**, not the model params.
- OOM (can't run both large models at full precision) → NVFP4 diffusion, lower `--gpu-memory-utilization`, serve sequentially, or use a smaller AR baseline.
- SSD won't mount → format **exFAT** for Linux; verify mount/read at home before leaving.
- Headless box → plug a monitor or serve the dashboard locally.
- NemoClaw onboarding eats time → get it onboarded for the on-brief story if time allows, but never at the expense of a working demo.

### Suggested improvements / missing details
- `save_images.sh` (docker save of the vLLM + NIM images) is the single most overlooked prep item.
- Pre-write `start_models.sh --model-dir ... --port ... [--diffusion]` so step 3 is one command per model.
- Have the FastAPI+Transformers shim written and tested **on the laptop against the API shape** (not the GPU) before the box, so the floor path is plug-and-play.
- Ask organizers at the door whether the box already has the `:gemma4` image or a DiffusionGemma NIM pulled — if yes, your risk drops sharply.

---

## Integration & Demo (cross-cutting)

### Merge points
- **A↔B:** tool server wraps A's `step()`/`get_state()`. Test through NemoClaw as soon as the mock endpoint is up.
- **B↔NemoClaw:** tool server URL + agent config. Testable with a mock endpoint (e.g. `nemoclaw run --config nemoclaw/agent_config.mock.yaml`) before real models are up.
- **B↔C:** C5 telemetry JSONL. Testable via mock/replay with no GPU.
- **D↔NemoClaw:** model endpoint URLs in `agent_config.yaml`. The last seam to close — AR-first.

### GB10 first-hour gate (shared rule)
No one builds features on the box until `curl localhost:8001/v1/models` returns **AND** NemoClaw completes one tool call against it. Until then: A keeps refining sim, B keeps refining the NemoClaw tool server profile, C keeps building the dashboard against NemoClaw-shaped mock telemetry.

### Demo fallback ladder
| Tier | What you show | What you say |
|---|---|---|
| Best | NemoClaw UI + side-by-side counter; diffusion keeps the line moving | "NemoClaw orchestrates parallel generation for parallel control, fully local on GB10." |
| Good | NemoClaw + AR Gemma 4 + sim + latency dashboard | "Same always-on local agent via NemoClaw; diffusion path ready, AR running today." |
| Worst | NemoClaw + mock endpoint + oracle-backed sim + dashboard replay | "NemoClaw agent and tool schema proven; model bind pending first box boot." |

### Honesty guardrails (so we never invite a question we can't answer)
- Pitch "**NemoClaw orchestrating parallel generation for parallel control, running fully local**" — not "diffusion is fundamentally better."
- Drop "4×." Say **"~1.9× tokens/sec, ~3.3× faster end-to-end on longer outputs"**; report **TTFT separately** (diffusion's is higher by design).
- Never claim a benchmark number you didn't measure on the GB10 that day.

### Top shared risks
1. **DiffusionGemma serving on day-one aarch64 hardware** — mitigated by the serving ladder + AR-first + the 12:00 hard stop.
2. **Short-output latency race not favoring diffusion** — mitigated by long action blocks (C1) + honest TTFT-vs-total framing.
3. **Box bring-up eating the build window** — mitigated by docker-saved images, pinned scripts, and the laptop-green-before-first-contact rule.
4. **NemoClaw tool-call reliability with diffusion** — mitigated by hard schema on `step`, retry-once, then `hold_position`; tool server never raises an unhandled exception.
5. **VLA/video scope creep** — mitigated by keeping Phase 1 text + structured state and starting camera/video only after DiffusionGemma is working.

---

*Keep this doc the source of truth. Update the Shared Contracts section first whenever a seam changes — every role depends on those five.*