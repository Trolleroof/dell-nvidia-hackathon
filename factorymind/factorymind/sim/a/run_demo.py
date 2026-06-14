"""Full sim demo pipeline — smoke, verify poses, record replay PNGs.

    python -m factorymind.sim.a.run_demo
    python -m factorymind.sim.a.run_demo --skip-replay
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def _run(module: str, label: str) -> None:
    print(f"\n=== {label} ===")
    rc = subprocess.call([sys.executable, "-m", module], env=os.environ.copy())
    if rc != 0:
        raise SystemExit(f"{label} failed (exit {rc})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full simulation demo pipeline")
    parser.add_argument("--skip-replay", action="store_true", help="Skip PNG replay recording")
    args = parser.parse_args()

    os.environ.setdefault("FACTORYMIND_SIM_BACKEND", "mujoco")

    _run("factorymind.sim.a.smoke_test", "Smoke test")
    _run("factorymind.sim.a.verify_poses", "Pose verification")

    if not args.skip_replay:
        _run("factorymind.sim.a.run_oracle_replay", "Oracle replay (PNG sequence)")

    print("\n=== Demo pipeline complete ===")


if __name__ == "__main__":
    main()
