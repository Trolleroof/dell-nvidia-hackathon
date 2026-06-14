# FactoryMind — Simulation Engineer Quick Start

You own **Role A**: the cell sim exposed via `get_state()` / `step()` / `reset()`.

This repo ships a **mock cell** (no MuJoCo yet) plus an **MCP server** so the agent engineer (B) and Cursor can drive the sim through tools immediately.

## 1. One-time setup (Mac, ~2 min)

```bash
cd factorymind
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2. Verify the sim (no MCP, no GPU)

```bash
python -m factorymind.sim.smoke_test
```

Expected: `OK — task complete in N steps, 3 parts at station_1`

## 3. Connect MCP in Cursor

The project includes `.cursor/mcp.json`. After setup:

1. **Cursor Settings → MCP** — confirm `factorymind-sim` appears (or reload window).
2. In chat, ask: *"Reset the cell and show me the state"* — Cursor will call `reset_cell` / `get_cell_state`.

If the venv path differs, edit `.cursor/mcp.json` to point at your `python`.

### MCP tools exposed

| Tool | Purpose |
|------|---------|
| `reset_cell(seed)` | Reset episode |
| `get_cell_state()` | Returns C2 JSON |
| `step_cell(plan_json)` | Apply C1 `CellPlan` |
| `list_targets()` | Valid named targets |

Resources: `factorymind://schema/c1`, `factorymind://schema/c2`, `factorymind://targets`

## 4. HTTP mode (for NemoClaw / team testing)

```bash
python -m factorymind.sim.mcp_server --http --port 8765
# Endpoint: http://localhost:8765/mcp
```

## 5. Your build order (from roles.md)

1. Mock cell + C2 schema + oracle smoke test
2. MCP server wrapping the sim
3. **Next:** MJCF scene (2 arms, bin, station) — swap `MockCellEnv` internals for MuJoCo
4. Named-target pose lookup table (precomputed, no live IK)
5. Offscreen render → PNG for frontend (C)

## Contracts you co-own

- **C1** (`factorymind/agent/schemas.py`) — `CellPlan` / `RobotCommand` — coordinate with B
- **C2** (`factorymind/sim/mock_cell.py` → `get_state()`) — freeze with B before they wire the loop

## Test a step from Python (without MCP)

```python
from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.mock_cell import MockCellEnv

env = MockCellEnv()
env.reset(0)
plan = CellPlan(
    plan="Move robot 0 to bin_a",
    robots=[
        RobotCommand(id=0, action="move", target="bin_a", reason="Approach pick location."),
        RobotCommand(id=1, action="hold", target="home", reason="Idle."),
    ],
)
print(env.step(plan))
```
