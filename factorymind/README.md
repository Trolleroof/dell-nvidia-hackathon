# FactoryMind

Local multi-robot assembly cell controller for the Dell × NVIDIA GB10 hackathon.

## Quick start by role

| Role | Start here |
|------|------------|
| **A — Simulation** | [`factorymind/sim/a/README.md`](factorymind/sim/a/README.md) |
| **B — Agent** | `factorymind/agent/` (control loop, schemas, telemetry) |
| **C — Frontend** | `factorymind/demo/` (latency dashboard) |
| **D — Models & Box** | `scripts/` (serving, box bring-up) |

Project overview: [`../overview.md`](../overview.md) · Roles detail: [`../roles.md`](../roles.md)

## Install (Mac or GB10)

```bash
cd factorymind
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m factorymind.sim.a.smoke_test
```

Do **not** copy `.venv` between Mac and GB10 — install deps on each machine.

## File ownership

See [`CODEOWNERS.md`](CODEOWNERS.md). Simulation code lives under `factorymind/sim/a/` only.
