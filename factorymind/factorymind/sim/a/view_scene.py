"""Load the MuJoCo cell in the interactive viewer — demo-ready scenario reset.

Run:
    python -m factorymind.sim.a.view_scene
    python -m factorymind.sim.a.view_scene --scenario conveyor_feed

On macOS, `launch_passive` needs MuJoCo's GUI interpreter. This module
auto-relaunches via `.venv/bin/mjpython` when needed (same as `python ...`).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _reexec_with_mjpython_on_macos() -> None:
    """MuJoCo passive viewer on macOS only works under mjpython."""
    if sys.platform != "darwin" or Path(sys.executable).name == "mjpython":
        return
    mjpython = Path(sys.executable).with_name("mjpython")
    if not mjpython.is_file():
        return
    os.execv(str(mjpython), [str(mjpython), *sys.argv])


_reexec_with_mjpython_on_macos()

import mujoco
import mujoco.viewer

from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.a.config import SimConfig
from factorymind.sim.a.env_factory import create_cell_env
from factorymind.sim.a.render import (
    DASHBOARD_AZIMUTH,
    DASHBOARD_DISTANCE,
    DASHBOARD_ELEVATION,
    DASHBOARD_LOOKAT,
)


def _run_passive_viewer(env) -> None:
    advance_belt = getattr(env, "_advance_conveyor_belt", None)
    with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_SITE] = 0
        viewer.cam.lookat[:] = DASHBOARD_LOOKAT
        viewer.cam.distance = DASHBOARD_DISTANCE
        viewer.cam.elevation = DASHBOARD_ELEVATION
        viewer.cam.azimuth = DASHBOARD_AZIMUTH
        while viewer.is_running():
            mujoco.mj_step(env.model, env.data)
            if advance_belt is not None:
                advance_belt()
            viewer.sync()


def _run_blocking_viewer(env) -> None:
    print(
        "Note: using blocking viewer (belt animation disabled). "
        "For full passive viewer on macOS run: mjpython -m factorymind.sim.a.view_scene"
    )
    mujoco.viewer.launch(env.model, env.data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive MuJoCo cell viewer")
    parser.add_argument(
        "--scenario",
        default="conveyor_feed",
        choices=["default", "sort_green", "misaligned", "empty_bin", "conveyor_feed"],
        help="Reset pose for demo (default: conveyor_feed)",
    )
    args = parser.parse_args()

    cfg = SimConfig(backend="mujoco", scenario=args.scenario, default_seed=0)  # type: ignore[arg-type]
    env = create_cell_env(cfg)
    state = env.reset(0)

    if args.scenario == "conveyor_feed":
        env.step(
            CellPlan(
                plan="Demo pose — robot 0 at pick station.",
                robots=[
                    RobotCommand(
                        id=0,
                        action="move",
                        target="conveyor_pick",
                        reason="Show pick-and-place story in viewer.",
                    ),
                    RobotCommand(id=1, action="hold", target="home", reason="Stand clear."),
                ],
            )
        )
        state = env.get_state()

    print(f"Scenario: {state.get('scenario')}")
    print(f"Task: {state.get('task')}")
    print("Close the viewer window to exit.")

    try:
        _run_passive_viewer(env)
    except RuntimeError as exc:
        if "mjpython" in str(exc):
            _run_blocking_viewer(env)
        else:
            raise


if __name__ == "__main__":
    main()
