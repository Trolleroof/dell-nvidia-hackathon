# Simulation Engineer

**Code:** `factorymind/factorymind/sim/a/`  
**Status log:** [`factorymind/sim/a/ROLE_A_SIMULATION_ENGINEER.md`](../factorymind/sim/a/ROLE_A_SIMULATION_ENGINEER.md)

## Status (2026-06-14)

| Item | Status |
|------|--------|
| Mock + MuJoCo + smoke test | ✅ |
| Auto pose lookup + verify | ✅ |
| Render + oracle replay | ✅ 13-frame demo |
| Phase 1 state contract | ✅ structured sim state; add object colors for sorting tasks |
| Phase 2 VLA/video | ⏳ after DiffusionGemma is running |
| GB10 checklist | ✅ `GB10_CHECKLIST.md` |

```bash
cd factorymind && source .venv/bin/activate
python -m factorymind.sim.a.smoke_test
python -m factorymind.sim.a.verify_poses
python -m factorymind.sim.a.run_demo
```

Phase 1 uses ground-truth structured sim state for planning. If the demo task is "sort green boxes," expose color/object metadata through state first; camera/video/VLA is Phase 2 after DiffusionGemma is running.

Update the status log after each change.
