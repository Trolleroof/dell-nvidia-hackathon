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

## Pass criteria

- `OK [mock]` and `OK [mujoco]` from smoke test
- `All targets within 0.05 m` from verify_poses
- `replay/step_*.png` exists (≥ 10 frames) after run_demo
