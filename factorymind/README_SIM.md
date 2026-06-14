# FactoryMind — Simulation Engineer Quick Start

**Your workspace:** `factorymind/factorymind/sim/a/` — edit only there.

See **`factorymind/sim/a/README.md`** for the full playbook.

## Setup

```bash
cd factorymind
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -e .
python -m factorymind.sim.a.smoke_test
```

## Your files vs everyone else's

| You edit | Others edit |
|----------|-------------|
| `sim/a/*` | `agent/*` (B), `demo/*` (C), `scripts/*` (D) |

Tell Role B to import:

```python
from factorymind.sim.a import create_cell_env
env = create_cell_env()
```

## MCP in Cursor

Server module: `factorymind.sim.a.mcp_server` (configured in `.cursor/mcp.json`).

## Next: MuJoCo

1. Add MJCF under `sim/a/assets/`
2. Implement `MujocoCellEnv` in `sim/a/mujoco_cell.py`
3. Set `FACTORYMIND_SIM_BACKEND=mujoco` when ready

Interface stays the same — no merge conflicts with B.
