"""GB10 / headless checklist — run on the box (dry-run OK on Mac).

    python -m factorymind.sim.a.run_gb10_check
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


def _try_render(backend: str) -> bool:
    env = os.environ.copy()
    env["FACTORYMIND_SIM_BACKEND"] = "mujoco"
    env["MUJOCO_GL"] = backend
    env["FACTORYMIND_SIM_SKIP_MUJOCO"] = "0"
    print(f"\n--- Headless render (MUJOCO_GL={backend}) ---")
    rc = subprocess.call([sys.executable, "-m", "factorymind.sim.a.render_frame"], env=env)
    return rc == 0


def main() -> None:
    os.environ["FACTORYMIND_SIM_BACKEND"] = "mujoco"

    steps = [
        ("factorymind.sim.a.smoke_test", "Smoke test"),
        ("factorymind.sim.a.verify_poses", "Pose verification"),
        ("factorymind.sim.a.run_oracle_replay", "Replay PNGs"),
    ]

    for module, label in steps:
        print(f"\n=== {label} ===")
        rc = subprocess.call([sys.executable, "-m", module], env=os.environ.copy())
        if rc != 0:
            raise SystemExit(f"{label} failed")

    if platform.system() == "Linux":
        for gl in ("egl", "osmesa"):
            if _try_render(gl):
                print(f"Headless render OK with MUJOCO_GL={gl}")
                break
        else:
            print("WARN: headless render failed for egl and osmesa")
    else:
        print("\n--- Headless render (skipped on non-Linux; use run_all for Mac viewer) ---")
        if not _try_render("glfw"):
            print("WARN: render_frame failed — on GB10 set MUJOCO_GL=egl")

    replay = Path(__file__).resolve().parent / "frames" / "replay"
    n = len(list(replay.glob("*.png"))) if replay.is_dir() else 0
    print(f"\n=== GB10 check complete — {n} replay frames ===")
    if n < 10:
        raise SystemExit("Expected ≥ 10 replay PNGs")


if __name__ == "__main__":
    main()
