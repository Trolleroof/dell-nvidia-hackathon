# Simulation Engineer — Quick Start

**Workspace:** `factorymind/factorymind/sim/a/`  
**Status log:** [`factorymind/sim/a/ROLE_A_SIMULATION_ENGINEER.md`](factorymind/sim/a/ROLE_A_SIMULATION_ENGINEER.md)

## Setup

```bash
cd factorymind
source .venv/bin/activate
pip install -e .
python -m factorymind.sim.a.smoke_test
```

## Commands

| Command | What |
|---------|------|
| `python -m factorymind.sim.a.smoke_test` | mock + mujoco + render check |
| `python -m factorymind.sim.a.verify_poses` | EE reachability vs all targets |
| `python -m factorymind.sim.a.view_scene` | 3D viewer (`conveyor_feed` demo pose; auto-uses `mjpython` on macOS) |
| `python -m factorymind.sim.a.render_frame` | single PNG |
| `python -m factorymind.sim.a.run_all` | **Everything** — checks + replay + live 3D window |
| `python -m factorymind.sim.a.run_live_demo` | Live oracle in MuJoCo viewer only |
| `python -m factorymind.sim.a.run_team_feed` | isolated `diffusion_run.jsonl` + `ar_run.jsonl` + frames |
| `python -m factorymind.sim.a.run_team_feed --scenario sort_green` | green-box sorting demo |
| `python -m factorymind.sim.a.serve_team_feed` | HTTP serve telemetry + frames (:8766) |
| `python -m factorymind.sim.a.mcp_server` | MCP for Cursor |

MuJoCo: `export FACTORYMIND_SIM_BACKEND=mujoco`  
Scenarios: `export FACTORYMIND_SIM_SCENARIO=default|sort_green|misaligned|empty_bin|conveyor_feed`

**macOS viewer:** `view_scene` re-launches via `.venv/bin/mjpython` automatically. If the window still fails, run explicitly: `mjpython -m factorymind.sim.a.view_scene`

## Planning Scope

Phase 1 planning uses text instructions plus structured sim state. For example, "sort green boxes" should be represented by object metadata in `get_state()`, not by camera perception. Camera/video/VLA belongs to Phase 2 after DiffusionGemma is running.

## API

```python
from factorymind.sim.a import create_cell_env

env = create_cell_env()
env.get_state()
env.step(plan)
env.save_frame()  # mujoco only
```

Playbook: [`factorymind/sim/a/README.md`](factorymind/sim/a/README.md)
