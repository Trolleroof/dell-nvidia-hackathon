# GB10 / headless sim checklist

Run on the Dell Pro Max after `pip install -e .` in `factorymind/`.

## 1. Basic checks

```bash
cd ~/factorymind
source .venv/bin/activate
python -m factorymind.sim.a.smoke_test
python -m factorymind.sim.a.verify_poses
```

## 2. Headless render (if step_0000.png fails)

```bash
export MUJOCO_GL=egl          # Linux / GB10 — try first
# export MUJOCO_GL=osmesa     # fallback if EGL unavailable
export FACTORYMIND_SIM_BACKEND=mujoco
python -m factorymind.sim.a.render_frame
```

## 3. Full demo artifact

```bash
export FACTORYMIND_SIM_BACKEND=mujoco
python -m factorymind.sim.a.run_demo
ls factorymind/factorymind/sim/a/frames/replay/
```

## 4. Interactive viewer (if monitor attached)

```bash
python -m factorymind.sim.a.view_scene
```

## Pass criteria

- `OK [mock]` and `OK [mujoco]` from smoke test
- `All targets within 0.05 m` from verify_poses
- `replay/step_*.png` exists (≥ 10 frames) after run_demo
