# Role A — Simulation Engineer workspace

**You own everything under `factorymind/sim/a/`.** Edit only here so you never conflict with B/C/D.

## Folder map

| File / folder | Purpose |
|---------------|---------|
| `cell.py` | Mock cell (`MockCellEnv`) — your main logic today |
| `mujoco_cell.py` | MuJoCo backend (build here next) |
| `state.py` | C2 state types |
| `targets.py` | Named target → pose lookup |
| `config.py` | Backend switch (`mock` / `mujoco`) |
| `env_factory.py` | **Integration point for Role B** — `create_cell_env()` |
| `oracle.py` | Deterministic demo policy |
| `mcp_server.py` | MCP tools for Cursor |
| `smoke_test.py` | Your CI check |
| `assets/` | MJCF/XML meshes |

## Do not edit (other roles)

| Path | Owner |
|------|-------|
| `factorymind/agent/` | Role B (Agent) |
| `factorymind/demo/` | Role C (Frontend) |
| `scripts/` | Role D (Models & Box) |
| `agent/schemas.py` | Co-owned C1 — propose changes to B, don't silently change |

## Commands (your venv)

```bash
cd factorymind && source .venv/bin/activate

# Your smoke test
python -m factorymind.sim.a.smoke_test

# Your MCP server
python -m factorymind.sim.a.mcp_server
```

## What teammates import (tell B this)

```python
from factorymind.sim.a import create_cell_env

env = create_cell_env()
state = env.get_state()
env.step(plan)
```

They should **not** import `MockCellEnv` directly unless testing.

## Switching to MuJoCo later

1. Implement `MujocoCellEnv` in `mujoco_cell.py`
2. Add assets under `assets/`
3. Set `FACTORYMIND_SIM_BACKEND=mujoco` or change default in `config.py`

No other files need to change if the interface stays the same.

## Merge conflict tips

- Stay inside `sim/a/` for all sim work
- Top-level `sim/*.py` files are thin shims — leave them alone
- If C1 schema must change, edit `agent/schemas.py` with B in the loop (one PR, both review)
