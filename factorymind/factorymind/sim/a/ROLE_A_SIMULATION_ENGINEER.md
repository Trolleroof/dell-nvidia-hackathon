# Simulation Engineer — Status & Changelog

**Workspace:** `factorymind/sim/a/` · **Updated:** 2026-06-14

Append a changelog entry whenever you ship. Edit only under `sim/a/`.

---

## Current status

| Item | Status |
|------|--------|
| C2 state schema (`state.py`) | ✅ |
| Mock cell (`cell.py`) | ✅ |
| Oracle policy (`oracle.py`) | ✅ 12-step pick-and-place |
| Smoke test | ✅ mock + mujoco + 720p render |
| MCP server | ✅ |
| MuJoCo scene (`assets/cell.xml`) | ✅ dual Menagerie Franka pandas |
| Menagerie assets (`assets/menagerie/`) | ✅ vendored `panda.xml` + meshes |
| `build_cell.py` | ✅ MjSpec composer → `cell.xml` |
| `solve_poses.py` → `assets/poses.json` | ✅ offline DLS IK |
| `MujocoCellEnv` | ✅ 7-DOF joint control + interpolation |
| Pose lookup (`pose_lookup.py`) | ✅ loads `poses.json` |
| Pose verify (`verify_poses.py`) | ✅ arm0/+Y and arm1/-Y targets ≤ 5 cm |
| Offscreen render (`render.py`) | ✅ 1280×720 dashboard camera |
| Reset scenarios | ✅ `default`, `sort_green`, `misaligned`, `empty_bin` |
| Oracle replay frames | ✅ 13 PNGs in `frames/replay/` |
| Demo pipeline | ✅ `run_demo.py` |
| Dashboard frame contract | ✅ `frames/latest.png` + `latest.json` |
| MCP scenario reset | ✅ `reset_cell(scenario=...)` |
| GB10 headless guide | ✅ `GB10_CHECKLIST.md` |
| Phase 1 task state | ✅ `task` + `parts[].color` / `label` / `shape` |
| Team feed (`run_team_feed.py`) | ✅ isolated `diffusion_run.jsonl` + `ar_run.jsonl` |
| Colored part boxes (`build_cell.py`) | ✅ yellow / blue / green MJCF geoms |
| `sort_green` scenario | ✅ task-aware oracle (green boxes only) |
| Misaligned oracle recovery | ✅ per-part approach targets |
| C5 `frame_url` sync | ✅ `/sim/replay/step_XXXX.png` in telemetry rows |
| GB10 manifest | ✅ `run_gb10_check` → `telemetry/gb10_manifest.json` |
| Demo telemetry export | ✅ `run_team_feed` → `demo/static/*.jsonl` |
| Phase 2 VLA/video | ⏳ blocked until DiffusionGemma endpoint is green |

**Backend:** `mock` (default) · `FACTORYMIND_SIM_BACKEND=mujoco` for physics + frames

**Scenarios:** `FACTORYMIND_SIM_SCENARIO=default|sort_green|misaligned|empty_bin`

---

## Public API

```python
from factorymind.sim.a import create_cell_env

env = create_cell_env()
state = env.get_state()   # C2 JSON
env.step(cell_plan)       # CellPlan

# MuJoCo only:
env.save_frame()          # → sim/a/frames/step_XXXX.png (1280×720)
env.render_rgb()          # → H×W×3 uint8 array

# Dashboard (Role C): poll sim/a/frames/latest.png or latest.json
# Optional live feed during agent loop:
#   export FACTORYMIND_SIM_AUTO_FRAME=1
```

**Named targets:** `home`, `bin_a`, `bin_b`, `station_1`, `station_2`, `part_1`, `part_2`, `part_3`

## Handoff for B / C (no MuJoCo required on their side)

```bash
cd factorymind && source .venv/bin/activate
export FACTORYMIND_SIM_BACKEND=mujoco

# 1) Generate isolated per-model telemetry + frames
python -m factorymind.sim.a.run_team_feed
# or Phase 1 sorting demo:
python -m factorymind.sim.a.run_team_feed --scenario sort_green

# 2) Serve for dashboard (replay side-by-side)
python -m factorymind.sim.a.serve_team_feed
# Diffusion run:  http://localhost:8766/telemetry/diffusion_run.jsonl
# AR run:         http://localhost:8766/telemetry/ar_run.jsonl
```

**C2 extras for planners:** `task`, `scenario`, `parts[].color` / `label` / `shape`

**Phase 1 planning contract:** NemoClaw/DiffusionGemma should plan from text plus structured sim state. For tasks like "sort green boxes," use `parts[].color` in C2 — no camera perception required until Phase 2.

---

## Changelog

### 2026-06-14 — Misaligned recovery + frame-synced C5 + GB10 manifest

- `oracle.py` — misaligned / `grip_miss` uses per-part approach (`part_1` not `bin_a`).
- C5 rows include optional `frame_url` for dashboard frame sync during replay.
- `run_gb10_check` — scenario tests + `telemetry/gb10_manifest.json`.
- Smoke test covers `misaligned` on mock + MuJoCo.
- Dashboard `CellView` shows MuJoCo PNG when `frame_url` is present (`serve_team_feed` :8766).

### 2026-06-14 — Colored boxes + dashboard isolated replay hookup

- `part_catalog.py` — `BOX_RGBA` / `rgba_for_part()` for MuJoCo part geoms.
- Rebuilt `cell.xml` — yellow / blue / green boxes visible in renders.
- Smoke test covers MuJoCo `sort_green`.
- `run_team_feed` auto-copies isolated runs to `demo/static/` for Role C replay.
- Dashboard (static + Vite): **Isolated runs** button merges `diffusion_run.jsonl` + `ar_run.jsonl`.

### 2026-06-14 — Isolated telemetry runs + sort_green scenario

- `telemetry_bridge.py` — per-model C5 rows with `precision`; `diffusion_run.jsonl` / `ar_run.jsonl` paths.
- `run_team_feed.py` — writes separate isolated runs (matched NVFP4 placeholders) for dashboard replay.
- `sort_green` scenario — task "Sort the green boxes to station_1"; oracle + `is_task_done()` are color-aware.
- `part_catalog.py` — `parts_for_task()`, `is_task_done()` helpers for Phase 1 text sorting.
- Smoke test covers `sort_green` on mock backend.

### 2026-06-14 — Team integration feed (B/C handoff)

- C2 state now includes `task`, `scenario`, and per-part `color` / `label` / `shape` (Phase 1 sorting).
- `run_team_feed.py` — oracle episode → `telemetry/run.jsonl` + replay PNGs + `latest.png`.
- `serve_team_feed.py` — HTTP serve telemetry + frames for dashboard Live mode.
- `telemetry_bridge.py` — real `action_summary` + `sim_event` from sim steps (latency placeholders until B binds models).

### 2026-06-14 — Dashboard frame contract + scenario parity

- Added `frame_export.py` — every `save_frame()` publishes `frames/latest.png` + `frames/latest.json` (1280×720 metadata for Role C).
- `FACTORYMIND_SIM_AUTO_FRAME=1` — auto-render after each MuJoCo step (live dashboard feed).
- Mock cell now supports `misaligned` / `empty_bin` scenarios (matches MuJoCo).
- MCP: `reset_cell(seed, scenario)`, `get_latest_frame()`, resource `factorymind://frame/latest`.
- `run_gb10_check` auto-runs `solve_poses` when `poses.json` is stale.

### 2026-06-14 — Menagerie dual Franka upgrade

- Vendored Menagerie `franka_emika_panda` under `assets/menagerie/`.
- Added `build_cell.py` — composes dual pandas (MjSpec attach), table, C1 sites, free parts, `dashboard` camera.
- Rebuilt `assets/cell.xml` with 1280×720 offscreen framebuffer.
- Added `solve_poses.py` — damped-least-squares IK → `assets/poses.json`.
- Rewrote `pose_lookup.py` / `mujoco_cell.py` for 7-DOF joint targets and smooth interpolation between poses.
- `render.py` — fixed 1280×720 render from `dashboard` camera.
- Optional reset scenarios: `misaligned` (offset parts), `empty_bin` (no parts in bin) via `FACTORYMIND_SIM_SCENARIO`.
- `verify_poses.py` — arm0 covers +Y fixtures, arm1 covers -Y fixtures.
- All pipelines green: `smoke_test`, `verify_poses`, `run_demo`, `run_oracle_replay`.

### 2026-06-14 — Demo replay + GB10 checklist

- Fixed `save_frame()` paths — replay PNGs land in `frames/replay/` (13 frames).
- Added `run_demo.py` — one command: smoke → verify → replay.
- Added `GB10_CHECKLIST.md` — headless render + box validation steps.

### 2026-06-14 — Auto pose lookup + verification

- Added `pose_lookup.py` — derives `TARGET_QPOS` from MJCF site/body positions.
- Added `verify_poses.py` — checks EE reaches every target (≤ 5 cm).
- Added `run_oracle_replay.py` — saves PNG sequence under `frames/replay/`.

### 2026-06-14 — Offscreen render

- Added `render.py` (`CellRenderer`) and `render_frame.py` CLI.
- `MujocoCellEnv.save_frame()` / `render_rgb()` for headless PNG export.

### 2026-06-14 — MuJoCo backend green

- Fixed `cell.xml` inertial properties.
- `MujocoCellEnv` — reset / get_state / step / grip / release.
- Smoke test: mock + mujoco both pass.

### 2026-06-14 — Workspace + MCP

- All sim code under `sim/a/`.
- `env_factory.create_cell_env()` entry point.
- Mock cell, oracle, smoke test, MCP tools.

---

## Commands

```bash
cd factorymind && source .venv/bin/activate
pip install -e .

# Rebuild scene + poses after editing fixtures or arm mounts
python -m factorymind.sim.a.build_cell
python -m factorymind.sim.a.solve_poses

export FACTORYMIND_SIM_BACKEND=mujoco
python -m factorymind.sim.a.smoke_test
python -m factorymind.sim.a.verify_poses
python -m factorymind.sim.a.run_demo
python -m factorymind.sim.a.run_oracle_replay

# Optional scenarios
export FACTORYMIND_SIM_SCENARIO=misaligned   # or empty_bin
python -m factorymind.sim.a.smoke_test

python -m factorymind.sim.a.mcp_server
```

---

## Next steps

1. On GB10: follow `GB10_CHECKLIST.md` (`MUJOCO_GL=egl`, then `run_demo`).
2. Tune arm mount poses in `build_cell.py` if fixture layout changes.

---

## How to update this file

Add a dated section under **Changelog** and refresh **Current status** after each ship.
