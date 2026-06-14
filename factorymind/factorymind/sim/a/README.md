# Simulation Engineer workspace

**Edit only under `factorymind/sim/a/`.**

Status log: [`ROLE_A_SIMULATION_ENGINEER.md`](ROLE_A_SIMULATION_ENGINEER.md)

## Folder map

| File / folder | Purpose |
|---------------|---------|
| `cell.py` | Mock cell |
| `mujoco_cell.py` | MuJoCo physics backend |
| `render.py` | Offscreen PNG renderer |
| `render_frame.py` | CLI — capture one frame |
| `pose_lookup.py` | Auto joint targets from MJCF |
| `verify_poses.py` | EE reachability check |
| `run_oracle_replay.py` | PNG sequence demo |
| `state.py` | C2 state types |
| `targets.py` | Named target → pose / joint lookup |
| `config.py` | `mock` / `mujoco` backend switch |
| `env_factory.py` | `create_cell_env()` entry point |
| `oracle.py` | Deterministic pick-and-place policy |
| `mcp_server.py` | MCP tools for Cursor |
| `smoke_test.py` | Health check |
| `view_scene.py` | Interactive MuJoCo viewer |
| `assets/` | MJCF scene |
| `frames/` | Rendered PNG output (gitignored) |

## Commands

```bash
cd factorymind && source .venv/bin/activate

python -m factorymind.sim.a.smoke_test
python -m factorymind.sim.a.verify_poses
python -m factorymind.sim.a.view_scene
python -m factorymind.sim.a.render_frame
python -m factorymind.sim.a.run_oracle_replay
python -m factorymind.sim.a.mcp_server
```

## Backends

```bash
# mock (default)
python -m factorymind.sim.a.smoke_test

# MuJoCo physics + render
export FACTORYMIND_SIM_BACKEND=mujoco
python -m factorymind.sim.a.smoke_test
python -m factorymind.sim.a.render_frame
```

## Integration entry point

```python
from factorymind.sim.a import create_cell_env

env = create_cell_env()
state = env.get_state()
env.step(plan)
```

Stay inside `sim/a/` for all sim work. Top-level `sim/*.py` files are thin shims — do not edit.
