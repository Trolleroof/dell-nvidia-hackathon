# FactoryMind — file ownership (hackathon)

Edit only your role's folder to avoid merge conflicts.

| Role | Folder | Lead |
|------|--------|------|
| **A — Simulation** | `factorymind/factorymind/sim/a/` | Sim engineer · [status log](factorymind/sim/a/ROLE_A_SIMULATION_ENGINEER.md) |
| **B — Agent** | `factorymind/factorymind/agent/` | Agent engineer |
| **C — Frontend** | `factorymind/factorymind/demo/` | Frontend engineer |
| **D — Models & Box** | `factorymind/scripts/`, `factorymind/models/` | Infra |

## Shared contracts (coordinate before editing)

- **C1** `factorymind/agent/schemas.py` — A + B co-own
- **Integration** `factorymind/sim/a/env_factory.py` — A owns; B imports `create_cell_env()`

## Shims (do not edit)

`factorymind/sim/mock_cell.py`, `oracle.py`, `mcp_server.py`, `smoke_test.py` re-export from `sim/a/` for backwards compatibility.
