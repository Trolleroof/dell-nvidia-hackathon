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
| Smoke test | ✅ mock + mujoco |
| MCP server | ✅ |
| MuJoCo scene (`assets/cell.xml`) | ✅ |
| `MujocoCellEnv` | ✅ |
| Pose lookup (`targets.py`) | ✅ auto-derived from MJCF |
| Pose verify (`verify_poses.py`) | ✅ all targets ≤ 5 cm |
| Offscreen render (`render.py`) | ✅ |
| Oracle replay frames | ✅ 13 PNGs in `frames/replay/` |
| Demo pipeline | ✅ `run_demo.py` |
| GB10 headless guide | ✅ `GB10_CHECKLIST.md` |

**Backend:** `mock` (default) · `FACTORYMIND_SIM_BACKEND=mujoco` for physics + frames

---

## Public API

```python
from factorymind.sim.a import create_cell_env

env = create_cell_env()
state = env.get_state()   # C2 JSON
env.step(cell_plan)       # CellPlan

# MuJoCo only:
env.save_frame()          # → sim/a/frames/step_XXXX.png
env.render_rgb()          # → H×W×3 uint8 array
```

**Named targets:** `home`, `bin_a`, `bin_b`, `station_1`, `station_2`, `part_1`, `part_2`, `part_3`

---

## Changelog

### 2026-06-14 — Demo replay + GB10 checklist

- Fixed `save_frame()` paths — replay PNGs land in `frames/replay/` (13 frames).
- Added `run_demo.py` — one command: smoke → verify → replay.
- Added `GB10_CHECKLIST.md` — headless render + box validation steps.
- **Next:** run `run_demo` on GB10 with `MUJOCO_GL=egl`.

### 2026-06-14 — Auto pose lookup + verification

- Added `pose_lookup.py` — derives `TARGET_QPOS` from MJCF site/body positions.
- Added `verify_poses.py` — checks EE reaches every target (≤ 5 cm).
- Added `run_oracle_replay.py` — saves PNG sequence under `frames/replay/`.
- Fixed duplicate part site names in `cell.xml`; added `bin_b`, `station_2`.
- Arms snap via direct qpos (no slow actuator lag); collision events in step.
- **Next:** optional Menagerie arm swap; GB10 headless test (`MUJOCO_GL=egl`).

### 2026-06-14 — Offscreen render

- Added `render.py` (`CellRenderer`) and `render_frame.py` CLI.
- `MujocoCellEnv.save_frame()` / `render_rgb()` for headless PNG export.
- MCP tool `render_cell_frame`.
- Frames land in `sim/a/frames/` (gitignored PNGs).
- **Next:** tune `TARGET_QPOS`; optional Menagerie arm swap in `cell.xml`.

### 2026-06-14 — MuJoCo backend green

- Fixed `cell.xml` inertial properties.
- `MujocoCellEnv` — reset / get_state / step / grip / release.
- `TARGET_QPOS` + `TARGET_QPOS_ARM1` in `targets.py`.
- Smoke test: mock + mujoco both pass.

### 2026-06-14 — MuJoCo scaffold

- `assets/cell.xml`, `view_scene.py`, `mujoco_cell.py` started.
- Added `mujoco`, `numpy` to requirements.

### 2026-06-14 — Workspace + MCP

- All sim code under `sim/a/`.
- `env_factory.create_cell_env()` entry point.
- Mock cell, oracle, smoke test, MCP tools.

---

## Commands

```bash
cd factorymind && source .venv/bin/activate
pip install -e .

python -m factorymind.sim.a.smoke_test
python -m factorymind.sim.a.view_scene
python -m factorymind.sim.a.verify_poses
python -m factorymind.sim.a.render_frame
python -m factorymind.sim.a.run_oracle_replay
FACTORYMIND_SIM_BACKEND=mujoco python -m factorymind.sim.a.render_frame

python -m factorymind.sim.a.mcp_server
```

---

## Next steps

1. On GB10: follow `GB10_CHECKLIST.md` (`MUJOCO_GL=egl`, then `run_demo`).
2. Optional: swap Menagerie arms in `assets/cell.xml`.

---

## How to update this file

Add a dated section under **Changelog** and refresh **Current status** after each ship.
