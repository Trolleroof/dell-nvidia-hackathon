"""Capture a single PNG from the MuJoCo cell (headless).

Run:
    python -m factorymind.sim.a.render_frame
    python -m factorymind.sim.a.render_frame --out /tmp/cell.png
"""

from __future__ import annotations

import argparse

from factorymind.sim.a.mujoco_cell import MujocoCellEnv


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one cell frame to PNG")
    parser.add_argument("--out", type=str, default=None, help="Output PNG path")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    env = MujocoCellEnv(seed=args.seed)
    path = env.save_frame(args.out)
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
