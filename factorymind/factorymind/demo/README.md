# Role C — Diffusion-vs-AR Latency Dashboard

The visible proof. When the diffusion line keeps moving while the AR baseline
stutters, the clock makes the argument — **parallel generation for parallel
control, running fully local on the GB10.**

Two builds of the same dashboard ship side-by-side (per the role brief):

| Build | Path | When to use |
|-------|------|-------------|
| **Static fallback** | [`static/index.html`](static/index.html) | The robust demo. One self-contained file, **zero dependencies**, no CDN, no build step. Double-click it or serve the folder. Survives an unfamiliar aarch64 / DGX OS box with **no outbound internet**. |
| **Polished** | [`dashboard/`](dashboard/) | React + TypeScript + Vite + Tailwind + Recharts. Built to static assets (`npm run build`) that also serve offline. |

Both consume the **frozen C5 telemetry schema** and run in three modes, all with
**no GPU**:

- **Mock Live** — synthetic fast (diffusion) / slow (AR) timings generated in the
  browser. Rehearse the whole narrative before the box exists.
- **Replay** — load a recorded `.jsonl` (the worst-case demo / safety net).
- **Live Feed** — poll Role B's telemetry JSONL (tail), e.g. `../../telemetry/run.jsonl`.

## What it shows

- **Cell view** — clean schematic of the 2-arm cell (or numbers-only).
- **Latency race** — side-by-side DiffusionGemma vs Gemma 4 (AR): tok/s, TTFT,
  total ms per decision.
- **Throughput-over-time** and **end-to-end latency-over-time** charts.
- **Parsed action stream** — the `CellPlan` summaries with parse/retry/event pills.
- **Aggregate stats** — mean / p50 / p95 latency, mean TTFT, parse-success rate.
- **Honest winner** — tok/s and end-to-end ratios computed *from the data*, with
  TTFT reported separately (diffusion's is higher by design).
- **Cloud (simulated) toggle** — adds a network round-trip lane to dramatize the
  on-prem / latency thesis.

## C5 telemetry schema (the only data source)

One JSON line per model per control step:

```json
{"ts": 0.0, "step": 42, "model": "diffusiongemma|gemma4|mock|oracle",
 "endpoint": "http://localhost:8000/v1", "latency_ms": 0, "ttft_ms": 0,
 "prompt_tokens": 0, "completion_tokens": 0, "parsed_ok": true, "retries": 0,
 "action_summary": "r0 move bin_a; r1 grip part_3", "sim_event": "pick_success"}
```

`tokens/sec` is derived client-side as `completion_tokens / ((latency_ms - ttft_ms) / 1000)`.

## Mock telemetry generator

[`gen_mock_telemetry.py`](gen_mock_telemetry.py) is a GPU-free stand-in for Role
B's telemetry writer (mirrors the in-browser mock engine).

```bash
# from factorymind/factorymind/demo/

# recorded file for Replay mode:
python gen_mock_telemetry.py --steps 80 --out static/sample_telemetry.jsonl

# stream forever into the shared telemetry dir for Live mode:
python gen_mock_telemetry.py --stream --out ../../telemetry/run.jsonl
```

A ready-made [`static/sample_telemetry.jsonl`](static/sample_telemetry.jsonl) is
checked in for instant Replay demos.

## Running

### Static (no toolchain)

```bash
# just open it
start static/index.html          # Windows
open  static/index.html          # macOS

# or serve the folder (needed for Live mode / fetch):
python -m http.server 8080 --directory static
# -> http://localhost:8080
```

### Polished (React / Vite)

```bash
cd dashboard
npm install
npm run dev        # http://localhost:5173
npm run build      # -> dist/ (static, offline-servable)
npm run preview    # serve the built dist/
```

> On the box: serve the build locally and open it in the **box's browser** — never
> SSH X-forwarding (too laggy). If the Vite build fights the aarch64 box, ship the
> static `index.html` — that's exactly why it exists.

## Theme

Dell × NVIDIA: pure-black canvas, **NVIDIA green = DiffusionGemma (hero)**,
**Dell blue = Gemma 4 AR (baseline)**, violet = simulated cloud. Bold, high-contrast,
room-legible across a venue.
