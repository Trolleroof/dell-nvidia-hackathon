# FactoryMind — Team Roles & Responsibilities

**Project:** FactoryMind — an always-on, fully-local controller agent for a multi-robot assembly cell, powered by DiffusionGemma on the Dell Pro Max with GB10.
**Event:** Dell × NVIDIA "Local AI on Dell Pro Max with GB10" hackathon · June 14, 2026 · build window 10:00 → 18:00.
**One-line thesis:** A factory floor can't send data to the cloud and can't tolerate latency, so the controller runs local, always-on, and fast — one persistent agent coordinating a cell of robot arms, replanning in real time, entirely on the box.

> **North-star ship order (do not reorder):**
> 1. Sim + control loop with **mock** LLM (runs on any laptop, zero GPU).
> 2. Same loop on the box with **AR Gemma 4** (the safe, known model).
> 3. Side-by-side **diffusion-vs-AR latency dashboard**.
> 4. **DiffusionGemma** hero path, *if* steps 1–3 are green.
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
JSON-serializable. What `get_state()` returns and what B feeds the model.

```json
{
  "step": 42,
  "robots": [{"id": 0, "pose": "...", "gripper": "open|closed", "holding": "part_3|null"}],
  "parts":  [{"id": "part_3", "pos": [0,0,0], "at": "bin_a|station_1|gripper_0|..."}],
  "stations": [{"id": "station_1", "status": "empty|occupied|done"}],
  "events": ["pick_success", "collision", "task_complete"],
  "done": false
}
```

### C3 — LLMClient interface (owned by B, used by everyone)
One interface, swappable backends. No business logic anywhere else touches a URL.

```python
class LLMClient(Protocol):
    def plan(self, state: dict) -> tuple[CellPlan, Telemetry]: ...

# MockClient(scripted JSON)        — laptop dev + CI, zero GPU
# OpenAICompatClient(base_url, m)   — real box endpoints, /v1/chat/completions
# OracleClient(sim)                 — deterministic correct actions, no model (demo floor)
```

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
│   ├── sim/            # A:  scene, get_state(), step(), smoke_test, oracle policy
│   ├── agent/          # B:  loop, schemas, llm_client (mock/openai/oracle), telemetry
│   └── demo/           # C:  dashboard (static-HTML + Vite), replay mode
├── scripts/            # D:  box_setup.sh, start_models.sh, run_demo.sh, save_images.sh
├── models/             # D:  (gitignored) NVFP4 diffusion + AR weights, copied from SSD
├── telemetry/          # B→C runtime JSONL
├── requirements.txt    # pinned; pip install ON THE BOX (no Mac wheels)
└── README.md
```

---

## Role A — Simulation Engineer

### Purpose
Own the physical world the agent controls. Provide a clean, deterministic `get_state()` / `step()` interface that hides all physics from the rest of the team, so B can drive it and C can show it without ever touching MuJoCo.

### Main responsibilities
- Author the MuJoCo cell: **2 robot arms** (use existing models — MuJoCo Menagerie / robosuite — do **not** build arms from scratch), a table, parts, and bins/stations, doing **one** task (pick-and-place / sort / stack).
- Implement `reset(seed)`, `get_state()` (returns C2), and `step(actions: CellPlan)` (apply per-robot commands, advance physics, return new state + events).
- Map high-level named targets (`"bin_a"`, `"station_1"`) to actuator/joint goals via a **precomputed lookup table of poses** — avoid live inverse kinematics under time pressure.
- Provide a deterministic **oracle policy** (scripted correct actions) so the loop and dashboard work with no model at all.
- Offscreen-render a frame for the dashboard and (optional) for the multimodal replanning story.

### Required tools, skills, technologies
MuJoCo (`mujoco` Python bindings: `MjModel`, `MjData`, `mj_step`, `Renderer`), MJCF/XML scene authoring, offscreen/EGL headless rendering, NumPy, basic robotics intuition. **Fallback engine:** PyBullet if MuJoCo headless GL on aarch64/DGX OS misbehaves.

### Inputs and expected outputs
- **Inputs:** parsed `CellPlan` from B; config (task params, seed, N arms).
- **Outputs:** C2 state object (to B), rendered frames (to C), episode events. All JSON-serializable.

### Step-by-step workflow
1. Stand up the MJCF scene with 2 arms + parts; confirm it loads and renders.
2. Define and freeze the C2 state schema with B.
3. Implement `reset` / `get_state` / `step`; clamp out-of-range targets.
4. Build the named-target → pose lookup table.
5. Write the **oracle policy** and a `smoke_test` (`python -m factorymind.sim.smoke_test`): arms complete the task end-to-end with no LLM.
6. Add offscreen render → PNG/np frame for C; expose a "misaligned part" / "empty bin" scenario for replanning.
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
- Headless render fails → degrade to state-only telemetry (dashboard shows numbers, no video).

### Suggested improvements / missing details
- Parameterize for N arms but **ship with 2**; only add the 3rd if everything is green by 15:00.
- Reuse a robosuite pick-and-place task rather than authoring physics.
- Precompute poses; no live IK.
- The oracle policy is the highest-leverage safety net you can build — do it early.

---

## Role B — Agent Engineer (Control Loop, Schemas, Mock LLM, Telemetry)

### Purpose
Own the brain: the always-on loop that reads state, asks the model for a `CellPlan`, validates it hard, steps the sim, and logs telemetry. Own the model-agnostic `LLMClient` and the JSON schema that is the project's central contract.

### Main responsibilities
- Define and own C1 (schema), C3 (LLMClient), C5 (telemetry).
- Implement the control loop: **read → prompt → call model → parse → validate → retry once → step → log → repeat.**
- Build the prompt (system + 1–2 golden examples + current state + schema instructions); instruct the model to return **only** valid JSON.
- Ship `MockClient` (scripted, deterministic — laptop/CI), `OpenAICompatClient(base_url, model)` (real endpoints), and wire A's `OracleClient`.
- Hard parsing: on failure, reprompt once; on second failure, **hold position** (last valid action / no-op) and log `parsed_ok=false`.
- Instrument latency, **time-to-first-token (separately)**, token counts → telemetry JSONL.

### Required tools, skills, technologies
Python, Pydantic v2, the `openai` client (OpenAI-compatible `/v1/chat/completions`), structured output / JSON-schema-guided decoding, prompt engineering, `httpx`/async for clean latency measurement, logging. *(This is the FastAPI/LangGraph wheelhouse — staff it with the strongest Python person.)*

### Inputs and expected outputs
- **Inputs:** C2 state from A; endpoint info (C4) from D; schema (co-owned with A).
- **Outputs:** validated `CellPlan` → A's `step()`; telemetry JSONL → C; the `LLMClient` + schema the whole team codes against.

### Step-by-step workflow
1. Define C1 + two golden example outputs.
2. Write `MockClient` returning schema-valid JSON; get the loop running against A's sim with **zero GPU**.
3. Implement `OpenAICompatClient` (structured output via `response_format`/guided JSON, or tool-calling with the `gemma4` parser).
4. Implement parse → retry-once → hold-position.
5. Instrument latency / TTFT / tokens → JSONL (C5).
6. On the box: swap `MockClient` → `OpenAICompatClient(AR_URL)`; confirm the loop drives the real cell.
7. For the race: run two clients (`DIFFUSION_URL`, `AR_URL`) over **identical state, identical max-tokens**, log both.

### Collaboration
- **With A:** co-own C1; consume C2; use the oracle as a client.
- **With D:** the C4 endpoint contract is your handoff — confirm model name, structured-output support, `max_model_len`.
- **With C:** freeze C5 telemetry fields and transport (SSE/websocket or tail-JSONL) up front; C builds against it immediately.

### Edge cases, limitations, failure handling
- Malformed/again-malformed JSON (diffusion can emit layout artifacts) → retry once → hold position; never block the loop.
- Model wraps JSON in prose → extract/strip before parsing; prefer guided-JSON decoding to prevent it.
- Endpoint down / latency spike → timeout → hold + log.
- **Diffusion structured-output reliability is the key unknown** → constrain hard, use the `gemma4` tool-call/reasoning parser, keep the canvas tight.
- Fairness of the race → identical prompts/limits/machine; report **TTFT separately from total** since diffusion's TTFT is higher by design.
- Runaway retries → cap at 1 and always advance the sim.

### Suggested improvements / missing details
- Use vLLM **guided JSON / structured outputs** to nearly eliminate parse failures.
- Log enough to compute mean/p50/p95 latency and parse-success rate for the pitch.
- Make the action block deliberately long (C1 note) so the speed delta is visible.
- Add a "replan on event" path (empty bin / misalignment) for the multimodal story.

---

## Role C — Frontend Engineer (Diffusion-vs-AR Latency Dashboard)

### Purpose
Own the visible proof. Build the local dashboard that makes the latency argument something judges *see*, plus the cell visualization. This is the persuasion surface — when the diffusion line keeps moving while AR stutters, the clock makes the argument.

### Main responsibilities
- Build a dashboard that **runs on the box and opens in the box's browser** (never SSH X-forwarding — it's laggy).
- Show: (1) the cell (A's frames, or a clean viz), (2) **side-by-side latency panels** — tokens/sec, TTFT, total ms, throughput-over-time, (3) the parsed action stream, (4) an aggregate stats panel.
- Consume C5 telemetry (live feed from B, or tail the JSONL).
- Make every number legible from across a room; show a clear "winner" indicator — honestly (see failure notes).
- Rehearse the whole narrative on a laptop with **mock fast/slow timings** before the box exists.

### Required tools, skills, technologies
React/TypeScript + Vite + Tailwind + a charting lib (Recharts/Chart.js) for the polished version. **Critical decision up front:** also build a **single static HTML + vanilla-JS** version — it's far more robust to serve on an unfamiliar box than a full Vite build on aarch64. SSE/websocket or polling for the live feed; `<img>`/canvas for frames.

### Inputs and expected outputs
- **Inputs:** C5 telemetry from B (fields + transport agreed up front); frames or state from A.
- **Outputs:** the dashboard on the projector; a clean screen recording + screenshots as the fallback artifact.

### Step-by-step workflow
1. Freeze C5 fields and transport with B.
2. Build the layout (cell view | dual latency panels | action stream | stats) against **mock** fast/slow data — rehearse the story with no GPU.
3. Wire to B's live feed; add a **replay mode** that plays a recorded JSONL.
4. Add the winner visual; show TTFT vs total honestly.
5. Make it room-legible (huge fonts, high contrast).
6. On the box: point at real endpoints, serve locally, confirm it opens in the box browser.
7. Capture a clean recording as the worst-case demo.

### Collaboration
- **With B:** total dependency on C5 — agree it first, build against mock data immediately.
- **With A:** render frames, or fall back to numbers-only if rendering is down.
- **With D:** coordinate the serve port and that it opens in the box's browser; ship the static-HTML version if the Vite build fights the box.

### Edge cases, limitations, failure handling
- No live telemetry yet → mock/replay mode (also the worst-case demo).
- Frames fail (headless render broken) → numbers-only latency race (still compelling).
- **Diffusion does NOT visibly win for short outputs** (the real risk) → rely on B's long blocks, report TTFT vs total honestly, and frame as "throughput on real work," not a rigged race.
- Projector/browser issues → screenshot deck + recording.
- Full Vite build fails on box → static-HTML fallback.

### Suggested improvements / missing details
- Build the static-HTML fallback **in parallel** with the Vite app, not after.
- Replay mode decouples you from a live box and *is* the worst-case demo — high priority.
- Add a "cloud (simulated, with network delay)" toggle to dramatize the on-prem/latency thesis.
- Keep a numbers-only mode that needs zero frames.

---

## NIKHIL PRABHU - Role D — Models & Box (Weights, Serving, Scripts, GB10 First Hour)

### Purpose
Own inference and the hardware. Get both models served locally on the GB10 behind OpenAI-compatible endpoints, own the first-hour bring-up, own every install script, and gate the team. **Most time-critical and highest-risk role — start at minute zero, staff it with the strongest infra person.**

### Main responsibilities
- Stage weights on SSD at home; copy to the box's internal NVMe day-of.
- Stand up serving with a **fallback ladder**, exposing `:8000` (diffusion) and `:8001` (AR).
- Own `scripts/box_setup.sh`, `start_models.sh`, `run_demo.sh`, and `save_images.sh`.
- Run the GB10 first-hour runbook and enforce the gate: **no feature work on the box until `curl localhost:8001/v1/models` succeeds.**
- Hand C4 (endpoints) to B; communicate clearly which models are actually up.
- (On-brief, time permitting) onboard NemoClaw/OpenShell so the "required stack" box is checked.

### Required tools, skills, technologies
vLLM via the **`vllm/vllm-openai:gemma4` Docker image** (stock `pip install vllm` likely lacks DiffusionGemma support — it's days old); **NVIDIA NIM** (containerized DiffusionGemma microservice, the easiest one-command path on NVIDIA HW); **HF Transformers + NVFP4** wrapped in a tiny FastAPI `/v1/chat/completions` shim (the floor — runs on DGX Spark out of the box); Docker + NVIDIA Container Toolkit; `rsync`/`lsblk`/`mount`; systemd; bash; ARM64/DGX OS; `hf download`.

**Weights (download at home):**
- Hero: **`nvidia/diffusiongemma-26B-A4B-it-NVFP4`** (~13–18 GB, NVFP4, NVIDIA-optimized) — use this, *not* the larger BF16 `google/diffusiongemma-26B-A4B-it`.
- Baseline: **`google/gemma-4-26B-A4B-it`** (AR, same MoE family). On 128 GB unified, NVFP4 diffusion (~18 GB) + BF16 AR (~52 GB) fits with headroom; use an NVFP4 AR variant if you want a lighter, fairer pair.

### Inputs and expected outputs
- **Inputs:** SSD with weights + scripts + saved Docker images + `nemoclaw.sh`; the GB10 (first contact day-of); organizer answers (is NemoClaw pre-installed? is there a monitor? SSH host?).
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
- NemoClaw/OpenShell onboarding eats time → get it onboarded for the on-brief story if time allows, but never at the expense of a working demo.

### Suggested improvements / missing details
- `save_images.sh` (docker save of the vLLM + NIM images) is the single most overlooked prep item.
- Pre-write `start_models.sh --model-dir ... --port ... [--diffusion]` so step 3 is one command per model.
- Have the FastAPI+Transformers shim written and tested **on the laptop against the API shape** (not the GPU) before the box, so the floor path is plug-and-play.
- Ask organizers at the door whether the box already has the `:gemma4` image or a DiffusionGemma NIM pulled — if yes, your risk drops sharply.

---

## Integration & Demo (cross-cutting)

### Merge points
- **A↔B:** `CellPlan` in, state out. Testable the moment both exist (via MockClient + smoke_test).
- **B↔C:** telemetry JSONL. Testable via mock/replay with no GPU.
- **D↔B:** endpoint URLs. The last seam to close — and the riskiest, so AR-first.

### GB10 first-hour gate (shared rule)
No one builds features on the box until `curl localhost:8001/v1/models` returns. Until then: A keeps refining sim, B/C keep working against mock + replay. The laptop versions must be fully green before first contact.

### Demo fallback ladder
| Tier | What you show | What you say |
|---|---|---|
| Best | Side-by-side counter; diffusion keeps the line moving | "Parallel generation for parallel control — fully local on GB10." |
| Good | AR Gemma 4 loop + sim + latency architecture | "Same always-on local controller; diffusion path ready, AR running today." |
| Worst | Sim + oracle/replay of recorded outputs | "Control loop and schema proven; model bind pending first box boot." |

### Honesty guardrails (so we never invite a question we can't answer)
- Pitch "**parallel generation for parallel control, running fully local**" — not "diffusion is fundamentally better."
- Drop "4×." Say **"~1.9× tokens/sec, ~3.3× faster end-to-end on longer outputs"**; report **TTFT separately** (diffusion's is higher by design).
- Never claim a benchmark number you didn't measure on the GB10 that day.

### Top shared risks
1. **DiffusionGemma serving on day-one aarch64 hardware** — mitigated by the serving ladder + AR-first + the 12:00 hard stop.
2. **Short-output latency race not favoring diffusion** — mitigated by long action blocks (C1) + honest TTFT-vs-total framing.
3. **Box bring-up eating the build window** — mitigated by docker-saved images, pinned scripts, and the laptop-green-before-first-contact rule.
4. **Structured-output parse failures under diffusion** — mitigated by guided JSON + retry-once + hold-position.

---

*Keep this doc the source of truth. Update the Shared Contracts section first whenever a seam changes — every role depends on those five.*