# FactoryMind

**An always-on, fully-local controller agent for a multi-robot assembly cell — powered by DiffusionGemma on the Dell Pro Max with GB10.**

Built for the Dell x NVIDIA "Local AI on Dell Pro Max with GB10" hackathon.

---

## The pitch (one line)

A factory floor can't send its data to the cloud and can't tolerate latency, so the controller has to run **local, always-on, and fast** — one persistent agent coordinating a cell of robot arms, replanning in real time, entirely on the box.

## Why it wins

- **On-theme and on-brief:** an always-on business agent running locally on the GB10 via **NemoClaw only** — the required stack is the demo, not a footnote. No cloud round-trip; data stays on-prem; the agent harness is exactly what the sponsors built.
- **Architecturally honest:** DiffusionGemma generates a whole block of tokens *in parallel* per pass, instead of one token at a time. We frame each robot action plan as a structured block — all N robots' next moves emitted in a single parallel pass. Parallel generation for parallel control.
- **Visible proof, not a research claim:** the demo runs a side-by-side latency counter — DiffusionGemma controller vs. a standard autoregressive Gemma 4 controller driving the same cell, both orchestrated by NemoClaw. When the diffusion one keeps the line moving while the AR one stutters, the clock makes the argument. NemoClaw's own control UI is embedded in the dashboard so judges see the agent thinking in real time.

> **Framing discipline:** the slides say *"parallel generation for parallel control, running fully local"* — NOT *"diffusion is fundamentally better."* The second is a benchmark we can't run in a day; the first is visibly true in the demo and doesn't invite a question we can't answer.

## How it works

**NemoClaw is the always-on agent harness** — the required stack is the core, not a layer on top.

1. **NemoClaw starts the agent session**, configured with the local model endpoint and the sim's tool server URL
2. **Read** — NemoClaw calls the `get_state` tool → sim returns current cell state
3. **Plan** — NemoClaw prompts the local model with the state + tool schema; model returns a `CellPlan` as a tool call
4. **Validate** — the `step` tool enforces the hard schema; bad output → NemoClaw reprompts once; second failure → `hold_position` tool. Loop never blocks.
5. **Step** — sim advances; events emit (pick success, collision, task complete)
6. **Repeat** — NemoClaw keeps the agent loop running, always-on
7. **Render** — the frontend dashboard **embeds NemoClaw's control UI (`:8080`)** alongside the live latency race

Phase 1 task input: the user can give text like "sort the green boxes," and the sim exposes structured object state (ids, colors, positions, locations) through `get_state`. DiffusionGemma plans over that symbolic state; NemoClaw calls the tools.

Phase 2/ambitious VLA: after DiffusionGemma is running reliably, add MuJoCo camera frames or video plus a perception/VLA layer. Do not make this part of the critical path.

## Stack

- **Agent harness (central):** NemoClaw v0.0.55 — **installed and running on this box**. NemoClaw owns the always-on loop and is the only planned orchestration layer.
- **Tool server (B):** Python + FastAPI — exposes `get_state`, `step`, `hold_position` to NemoClaw. Schema-validates every `CellPlan` before touching the sim.
- **Task/state input:** Phase 1 uses text instructions plus ground-truth sim state, including object attributes like color for tasks such as "sort green boxes."
- **Model:** DiffusionGemma `nvidia/diffusiongemma-26B-A4B-it-NVFP4` (~18 GB) served at `:8000`; NemoClaw points at it.
- **Model staging status (June 14, 2026):** DiffusionGemma weights are already staged locally at `/home/dell/factorymind/models/diffusiongemma` and on the SSD at `/media/dell/T9/factorymind/models/diffusiongemma`; Gemma 4 AR is staged in the matching `gemma4-ar` paths as the fallback baseline.
- **Fallback model:** Gemma 4 AR at `:8001` — same NemoClaw loop, same tools, loses the diffusion speed story but keeps the whole demo.
- **Sim:** MuJoCo (PyBullet fallback) — 2 robot arms, one pick-and-place task. Use an existing model; do not build physics.
- **Frontend:** React/Vite dashboard + static-HTML fallback; **embeds NemoClaw control UI (`:8080`)** in an iframe.
- **Hardware:** Dell Pro Max with GB10 — GB10 Grace Blackwell Superchip, 128 GB unified memory, **aarch64 / DGX OS (Ubuntu 24.04)**

## Constraint: no GB10 before hackathon day

We do **not** have SSH or physical access to the Dell Pro Max / GB10 ahead of time. That means:

- We **cannot** validate DiffusionGemma, vLLM, or NemoClaw on the actual box early.
- We **can** build and fully test everything that doesn't need GB10 CUDA: sim, JSON schema, NemoClaw mock loop, latency UI, install scripts.
- **First contact with the box = install + debug hour.** Plan the demo so it still ships if that hour goes badly.

> Treat the Mac as the **factory blueprint**. Treat hackathon morning as **turning the machines on for the first time**.

## Scope guardrails (so it ships 10:00 → 18:00)

- 2 robot arms, **one** assembly task. One cell, not a factory. (Drop the third arm unless everything else is green by 15:00.)
- **Ship order:** (1) sim tool server + NemoClaw agent with mock endpoint → (2) same NemoClaw loop on box with AR Gemma 4 → (3) side-by-side latency counter with NemoClaw UI embedded → (4) DiffusionGemma hero path if time.
- Constrain model output to a tight JSON schema; parse hard. Reliability > cleverness.
- **Primary fallback is the plan, not a panic button:** same loop on standard AR Gemma 4. Demo still works; we lose the diffusion speed story, not the whole project.
- **No camera/video/VLA in the critical path.** Phase 1 is text + structured sim state. Phase 2 starts only after AR, NemoClaw, dashboard, and DiffusionGemma are green.

## Critical risks (revised for no pre-access)

- **ARM64 Linux, not Mac.** DGX OS is Ubuntu on `aarch64`. Do not copy Mac `pip` packages or binaries to the box. Only copy **source code, model weights, and shell scripts**; install Python deps *on the box* with `pip install`.
- **DiffusionGemma is day-one unknown.** Without the box, we can't pre-test the diffusion sampler. Write `scripts/box_setup.sh` now; run it first thing on the GB10. If DiffusionGemma fails by 12:00, **stop debugging it** and demo AR Gemma 4 + the architecture story.
- **Install time eats the hackathon.** Assume 60-90 minutes of pure setup on first SSH. No feature work until `curl localhost:8001/v1/models` succeeds and NemoClaw can make one tool call.
- **Display for the demo.** SSH X-forwarding is laggy. Plug a monitor into the box, or render sim frames to a local HTML dashboard the judges open in a browser on the box.

## Two-phase workflow

### Phase A — on your Mac (now → night before)

**Goal:** arrive with a repo that runs end-to-end against a **mock endpoint through NemoClaw**. Zero GB10 required.

1. **Sim + NemoClaw loop** — PyBullet, 2 arms, one pick-and-place task, headless OK.
2. **Hard JSON schema** — Pydantic model for `CellPlan`; reject bad output, retry once, then hold position. Include structured object attributes in state so text tasks like "sort green boxes" can be planned without camera perception.
3. **Latency counter UI** — same dashboard code; on Mac, feed it fake timings or two mock endpoints with artificial delay (fast vs slow) so the *demo narrative* is rehearsed.
4. **NemoClaw config profiles** — one NemoClaw path, three endpoint profiles:
   - `mock` — fixed local responses for Mac dev + CI
   - `ar` — `AR_URL=http://localhost:8001/v1`
   - `diffusion` — `DIFFUSION_URL=http://localhost:8000/v1`
5. **Install scripts (untested on real HW, but written)** — `scripts/box_setup.sh`, `scripts/start_models.sh`, `scripts/run_demo.sh`. Document every command; no manual steps from memory.
6. **Hard drive staging** — download model weights + project onto an external SSD at home. Copy onto the GB10 at the venue (see below). Do **not** copy Mac Python packages.

## Phase 2/Ambitious VLA Path

Only start this after the core loop is green: NemoClaw can call tools, AR works on `:8001`, DiffusionGemma works on `:8000`, and the dashboard is live. The VLA path adds MuJoCo camera frames or video, a perception/VLA step that identifies objects such as green boxes, and then feeds the resulting object list back into the same NemoClaw tool loop. If DiffusionGemma video input is not proven on the box, use a separate detector/vision model and keep DiffusionGemma as the text planner.

Do not pitch Phase 2 as shipped unless it is actually running. The shipped demo remains text instruction + structured sim state + NemoClaw tools.

## Hard drive plan (download at home → plug into GB10)

**Yes — this is the right move.** Venue Wi‑Fi is unreliable for 30–40 GB. Download everything at home on fast internet, bring the drive, copy to the box in minutes.

Think of the drive as a **pre-loaded ammo crate**: the bullets (weights) travel with you; the gun (vLLM) still gets assembled on the GB10.

### What to download (exact targets)

Create one folder on the drive so paths are predictable on the box:

```
/Volumes/T9/factorymind/          # Mac mount (T9 drive); /media/... on GB10 when plugged in
├── models/
│   ├── diffusiongemma/           # ~18–30 GB depending on quant
│   └── gemma4-ar/                # AR benchmark pair (~52 GB)
├── repo/
│   └── factorymind/              # this project (git clone or tarball)
├── scripts/
│   ├── nemoclaw.sh               # saved copy of installer
│   └── offline-notes.md          # vLLM serve commands, HF model IDs
└── MANIFEST.txt                  # file count + total size (verify copy succeeded)
```

**DiffusionGemma (hero model)**

- Hugging Face repo: `nvidia/diffusiongemma-26B-A4B-it-NVFP4`
- Use the **NVIDIA NVFP4** build as the default hero path — it fits the ~18 GB story in the pitch and matches the box-serving plan in the other docs.
- Download the **full snapshot** (config, tokenizer, weight shards) — not just a single `.gguf` unless your serve script explicitly uses llama.cpp.

**Gemma 4 AR (benchmark baseline)**

- Hugging Face repo: `google/gemma-4-26B-A4B-it` — same 26B A4B MoE family as DiffusionGemma, autoregressive path.
- ~52 GB on disk (matches diffusion full weights). Fair side-by-side on GB10: diffusion on `:8000`, AR on `:8001`.

### Download on your Mac (home Wi‑Fi)

```bash
# 1. Format drive: exFAT or APFS (exFAT if you might plug directly into GB10 Linux)
# 2. Install HF CLI once (`hf` — huggingface-cli is deprecated)
pip install -U huggingface-hub

# 3. Login if the repo is gated (accept license on huggingface.co first)
hf auth login

# 4. Download DiffusionGemma — resume-safe, do not interrupt
export DRIVE="/Volumes/T9/factorymind"
mkdir -p "$DRIVE/models/diffusiongemma"
hf download nvidia/diffusiongemma-26B-A4B-it-NVFP4 \
  --local-dir "$DRIVE/models/diffusiongemma"

# 5. Download AR fallback (replace REPO with the Gemma 4 model ID you settle on)
mkdir -p "$DRIVE/models/gemma4-ar"
hf download google/gemma-4-26B-A4B-it \
  --local-dir "$DRIVE/models/gemma4-ar"

# 6. Copy project + offline installer
mkdir -p "$DRIVE/repo" "$DRIVE/scripts"
cp -R ~/dellxnvidia-hackathon "$DRIVE/repo/factorymind"
curl -fsSL https://www.nvidia.com/nemoclaw.sh -o "$DRIVE/scripts/nemoclaw.sh"

# 7. Sanity check before unplugging
du -sh "$DRIVE/models/"*
find "$DRIVE/models/diffusiongemma" -name '*.safetensors' -o -name '*.bin' | head
```

**Before you leave home:** unplug and replug the drive; confirm files open. A incomplete download on site is worse than no download.

### Get it onto the GB10 (day-of, two options)

**Option A — USB into the GB10 (fastest, no network)**

1. Plug SSD into the Dell Pro Max.
2. Find mount point: `lsblk` then `sudo mount /dev/sdX1 /mnt/ssd` (or it auto-mounts under `/media/$USER/`).
3. Copy to local disk (serve from internal NVMe, not USB):

```bash
SSD=/media/$USER/T9/factorymind    # or /mnt/T9/factorymind — run `lsblk` / check Finder mount
mkdir -p ~/factorymind/models
rsync -ah --info=progress2 "$SSD/models/" ~/factorymind/models/
rsync -ah --info=progress2 "$SSD/repo/factorymind/" ~/factorymind/
```

**Option B — SSD on your Mac, copy over SSH**

```bash
SSD=/Volumes/T9/factorymind
rsync -ah --info=progress2 -e ssh \
  "$SSD/models/" user@GB10_HOST:~/factorymind/models/
rsync -ah --info=progress2 -e ssh \
  "$SSD/repo/factorymind/" user@GB10_HOST:~/factorymind/
```

Use Option A if the box has a USB port and you can touch it; Option B if the GB10 is headless and only SSH is available.

### Point the model server at local files (on GB10)

Weights on disk ≠ model running. After copy, start inference with **local paths**, not Hugging Face download:

```bash
# vLLM example — diffusion on :8000
vllm serve ~/factorymind/models/diffusiongemma \
  --host 0.0.0.0 --port 8000 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85 \
  --generation-config vllm \
  --hf-overrides '{"diffusion_sampler": "entropy_bound", "diffusion_entropy_bound": 0.1}' \
  --diffusion-config '{"canvas_length": 256}' \
  --enable-chunked-prefill

# AR fallback on :8001 (standard serve — exact flags depend on model format)
vllm serve ~/factorymind/models/gemma4-ar \
  --host 0.0.0.0 --port 8001 \
  --max-model-len 8192
```

Set in your app: `DIFFUSION_URL=http://localhost:8000/v1`, `AR_URL=http://localhost:8001/v1`.

### What the drive does NOT replace

| On the drive ✅ | Still install on GB10 ❌ |
|-----------------|-------------------------|
| Model weight files | vLLM / NemoClaw |
| Your Python source | `pip install -r requirements.txt` |
| Shell scripts | CUDA-aware runtime (first `pip install vllm` may compile) |
| Offline copy of `nemoclaw.sh` | Docker, `nemoclaw onboard` |

**Do not** copy a Mac `.venv` or Mac-built wheels to the box — only the weight files and source code from the drive.

### Drive checklist

- [ ] SSD 256 GB+ ( diffusion + AR + repo ≈ 40–60 GB with headroom )
- [ ] DiffusionGemma full HF snapshot on `models/diffusiongemma/`
- [ ] Gemma 4 AR snapshot on `models/gemma4-ar/`
- [ ] Project on `repo/factorymind/`
- [ ] `nemoclaw.sh` saved under `scripts/`
- [ ] Verified file sizes at home (`du -sh`, spot-check a `.safetensors` file)
- [ ] Know copy plan: USB mount **or** `rsync` over SSH

**Mac dev commands (sanity check without GB10):**

```bash
python -m venv .venv && source .venv/bin/activate
pip install pybullet numpy pydantic openai
python -m factorymind.sim.smoke_test          # sim loads, arms move
nemoclaw run --config nemoclaw/agent_config.mock.yaml   # full loop, mock endpoint
python -m factorymind.demo.latency_dashboard  # counter UI with fake timings
```

### Phase B — on the GB10 (hackathon morning, first 90 min)

**Goal:** replace mock with real local inference. Do not rewrite app logic on the box.

```bash
# Session 0 — confirm machine (30 sec)
uname -m                    # must: aarch64
nvidia-smi                  # GB10 visible
docker info >/dev/null      # Docker up

# Session 1 — tmux: agent stack (if not pre-installed by organizers)
tmux new -s stack
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
nemoclaw onboard            # pick LOCAL inference

# Session 2 — tmux: models (copy from drive first, then serve)
tmux new -s models
# If not already on disk: rsync from USB → ~/factorymind/models/  (see Hard drive plan)
./scripts/start_models.sh --model-dir ~/factorymind/models/gemma4-ar --port 8001
curl -s http://localhost:8001/v1/models

# Session 3 — tmux: app
tmux new -s demo
# repo already at ~/factorymind/ if you rsync'd from drive
cd ~/factorymind && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
nemoclaw run --config nemoclaw/agent_config.ar.yaml

# Only if AR loop works — diffusion from pre-staged weights on :8000
./scripts/start_models.sh --model-dir ~/factorymind/models/diffusiongemma --port 8000 --diffusion
```

**Remote dev:** VS Code Remote-SSH into the box once you have credentials. Edit on the box only for env-specific fixes; core logic should already work from Mac.

## Pre-stage checklist (no GB10 required)

**Mac — build & test**

- [ ] Sim runs headless; 2 arms complete one task
- [ ] NemoClaw mock loop runs; JSON parse + retry logic tested
- [ ] Latency dashboard runs with mock fast/slow backends
- [ ] NemoClaw config profiles; no hardcoded URLs in business logic
- [ ] `scripts/box_setup.sh`, `start_models.sh`, `run_demo.sh` written and reviewed
- [ ] `requirements.txt` pinned (PyBullet, pydantic, openai client only — no CUDA libs)

**Hard drive — download at home, copy on site**

- [ ] SSD 256 GB+ formatted (exFAT if plugging directly into GB10)
- [ ] `nvidia/diffusiongemma-26B-A4B-it-NVFP4` → `models/diffusiongemma/` (verified with `du -sh`)
- [ ] Gemma 4 AR fallback → `models/gemma4-ar/`
- [ ] Project → `repo/factorymind/`
- [ ] `nemoclaw.sh` + vLLM serve commands saved under `scripts/`
- [ ] Copy plan chosen: USB into GB10 **or** `rsync` over SSH from Mac

**Laptop — day-of logistics**

- [ ] VS Code Remote-SSH extension installed
- [ ] External SSD (256 GB+, SSD not thumb drive)
- [ ] Ask organizers: SSH host, is NemoClaw pre-installed?, is there a monitor?

**Explicitly NOT on this checklist (needs the box)**

- ~~DiffusionGemma load tested end-to-end~~ → becomes hour-1 box task
- ~~arm64 wheels pre-installed~~ → `pip install` on the box only
- ~~NemoClaw onboarded~~ → first tmux session on site

## Demo narratives (pick one live)

| Situation | What you show | What you say |
|-----------|---------------|--------------|
| **Best case** | Side-by-side counter; diffusion keeps line moving | "Parallel generation for parallel control — fully local on GB10." |
| **Good case** | AR Gemma 4 loop + sim + latency architecture | "Same always-on local controller; diffusion path ready, AR running today." |
| **Worst case** | NemoClaw + mock endpoint + replay dashboard | "NemoClaw agent and schema proven; model bind pending first box boot." |

Never claim benchmark numbers you didn't measure on the GB10 that day.

## Prize

1st place: a Dell Pro Max with GB10 (~$4k machine) per team. The judges are giving away their own sponsor hardware — a demo that shows *why this specific local box matters* is exactly what plays.
