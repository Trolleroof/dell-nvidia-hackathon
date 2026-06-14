"""Run every sim step: checks, replay PNGs, then open live viewer."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


def _mjpython() -> str | None:
    if platform.system() != "Darwin":
        return None
    for base in (os.environ.get("VIRTUAL_ENV"), sys.prefix):
        if not base:
            continue
        candidate = Path(base) / "bin" / "mjpython"
        if candidate.is_file():
            return str(candidate)
    return None


def _python_for_viewer() -> str:
    return _mjpython() or sys.executable


def _run(module: str, label: str) -> None:
    print(f"\n=== {label} ===")
    rc = subprocess.call([sys.executable, "-m", module], env=os.environ.copy())
    if rc != 0:
        raise SystemExit(f"{label} failed (exit {rc})")


def _open_replay_folder() -> None:
    replay = Path(__file__).resolve().parent / "frames" / "replay"
    if replay.is_dir() and platform.system() == "Darwin":
        subprocess.call(["open", str(replay)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Full sim build + live viewer")
    parser.add_argument("--skip-viewer", action="store_true", help="Skip opening MuJoCo window")
    args = parser.parse_args()

    os.environ["FACTORYMIND_SIM_BACKEND"] = "mujoco"

    _run("factorymind.sim.a.smoke_test", "1/4 Smoke test")
    _run("factorymind.sim.a.verify_poses", "2/4 Pose verification")
    _run("factorymind.sim.a.run_oracle_replay", "3/4 Replay PNGs")
    _open_replay_folder()

    if not args.skip_viewer:
        viewer_py = _python_for_viewer()
        print(f"\n=== 4/4 Live viewer (close window to finish) ===")
        print(f"Using: {viewer_py}")
        rc = subprocess.call(
            [viewer_py, "-m", "factorymind.sim.a.run_live_demo"],
            env=os.environ.copy(),
        )
        if rc != 0:
            raise SystemExit(f"Live viewer failed (exit {rc})")

    print("\n=== All sim steps complete ===")


if __name__ == "__main__":
    main()
