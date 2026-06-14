"""Live pick-and-place demo — opens MuJoCo viewer and runs the oracle.

    python -m factorymind.sim.a.run_live_demo

On macOS uses mjpython automatically (required for the viewer window).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def _ensure_mjpython() -> None:
    if sys.platform != "darwin" or os.environ.get("FACTORYMIND_MJPYTHON"):
        return
    for base in (os.environ.get("VIRTUAL_ENV"), sys.prefix):
        if not base:
            continue
        mjpython = Path(base) / "bin" / "mjpython"
        if mjpython.is_file():
            os.environ["FACTORYMIND_MJPYTHON"] = "1"
            os.execv(str(mjpython), [str(mjpython), *sys.argv])


_ensure_mjpython()

import mujoco.viewer

from factorymind.sim.a.mujoco_cell import MujocoCellEnv
from factorymind.sim.a.oracle import oracle_plan


def main() -> None:
    env = MujocoCellEnv(seed=0)
    env.reset(0)

    print("Opening MuJoCo viewer — close the window to exit.")
    print("Running oracle pick-and-place (3 parts → station_1)...")

    with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
        viewer.cam.azimuth = 120
        viewer.cam.elevation = -25
        viewer.cam.distance = 1.8
        viewer.cam.lookat[:] = [0.45, 0.0, 0.45]

        # Render every physics substep at (roughly) real time so the arm
        # animates smoothly instead of jumping once per high-level step.
        sim_dt = float(env.model.opt.timestep)
        next_frame = time.perf_counter()

        def on_substep() -> None:
            nonlocal next_frame
            if not viewer.is_running():
                return
            viewer.sync()
            next_frame += sim_dt
            delay = next_frame - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                # Fell behind real time — resync the clock to avoid runaway drift.
                next_frame = time.perf_counter()

        env._on_substep = on_substep

        # Show initial state
        viewer.sync()
        time.sleep(0.8)

        for _ in range(50):
            if not viewer.is_running():
                break
            state = env.get_state()
            if state["done"]:
                print(f"Task complete in {state['step']} steps.")
                time.sleep(2.0)
                break
            plan = oracle_plan(state)
            next_frame = time.perf_counter()
            env.step(plan)

        env._on_substep = None
        while viewer.is_running():
            viewer.sync()
            time.sleep(0.05)

    final = env.get_state()
    print(f"Done — step={final['step']}, placed={sum(1 for p in final['parts'] if p['at'] == 'station_1')}/3")


if __name__ == "__main__":
    main()
