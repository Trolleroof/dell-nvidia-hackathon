# GB10 / headless sim checklist

Run on the Dell Pro Max after `pip install -e .` in `factorymind/`.

## 1. Basic checks

```bash
cd factorymind && source .venv/bin/activate
export FACTORYMIND_SIM_BACKEND=mujoco
python -m factorymind.sim.a.run_gb10_check   # Mac dry-run OK
```

On GB10 (Linux only — do **not** set MUJOCO_GL before import on Mac):

```bash
export FACTORYMIND_SIM_BACKEND=mujoco
export MUJOCO_GL=egl          # set only for render on the box
python -m factorymind.sim.a.run_gb10_check
```

## 4. Interactive viewer (if monitor attached)

```bash
python -m factorymind.sim.a.view_scene
```

## Scope note

This checklist validates the Phase 1 sim path only: structured C2 state, MuJoCo frames, and NemoClaw tool readiness. Do not spend GB10 bring-up time on camera/video/VLA until AR, NemoClaw, dashboard, and DiffusionGemma are already green.

## Pass criteria

- `OK [mock]` and `OK [mujoco]` from smoke test (includes `sort_green` + `misaligned`)
- `All assigned targets within 0.05 m` from verify_poses
- `replay/step_*.png` exists (≥ 10 frames) after run_oracle_replay
- `telemetry/gb10_manifest.json` written with `"ok": true`
- On GB10 Linux: headless render passes with `MUJOCO_GL=egl`
