# FactoryMind — Simulation

Local multi-robot assembly cell sim for the Dell × NVIDIA GB10 hackathon.

**Workspace:** `factorymind/sim/a/`  
**Status log:** [`sim/a/ROLE_A_SIMULATION_ENGINEER.md`](factorymind/sim/a/ROLE_A_SIMULATION_ENGINEER.md)  
**Quick start:** [`README_SIM.md`](README_SIM.md)

## Install

```bash
cd factorymind
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m factorymind.sim.a.smoke_test
```

Do **not** copy `.venv` between machines — run `pip install -e .` on each.

## Commands

```bash
python -m factorymind.sim.a.smoke_test
python -m factorymind.sim.a.view_scene
python -m factorymind.sim.a.render_frame
export FACTORYMIND_SIM_BACKEND=mujoco   # physics + PNG frames
```

Project docs: [`../overview.md`](../overview.md)
