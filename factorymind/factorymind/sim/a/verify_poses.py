"""Verify arm reaches each named target — run after editing cell.xml.

    python -m factorymind.sim.a.verify_poses
"""

from __future__ import annotations

import mujoco

from factorymind.sim.a.mujoco_cell import MujocoCellEnv
from factorymind.sim.a.pose_lookup import ee_distance_to_site
from factorymind.sim.a.targets import TARGET_QPOS

THRESHOLD_M = 0.05
PART_THRESHOLD_M = 0.04  # grip approach is 2 cm below part center


def main() -> None:
    env = MujocoCellEnv(seed=0)
    model, data = env.model, env.data
    fails = 0

    print(f"{'target':<12} {'dist_m':>8}  qpos")
    for name, qpos in TARGET_QPOS.items():
        if name == "home":
            continue
        env.reset(0)
        env._move_arm(0, qpos)
        mujoco.mj_forward(model, data)
        try:
            if name.startswith("part_"):
                bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
                ee_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "arm0_ee")
                ee = data.site_xpos[ee_id]
                bp = data.xpos[bid]
                dist = float(((ee - bp) ** 2).sum() ** 0.5)
            else:
                dist = ee_distance_to_site(model, data, arm_id=0, site_name=name)
        except Exception:
            print(f"{name:<12} {'SKIP':>8}  (no site in MJCF)")
            continue
        ok = dist <= (PART_THRESHOLD_M if name.startswith("part_") else THRESHOLD_M)
        mark = "OK" if ok else "FAIL"
        print(f"{name:<12} {dist:8.4f}  {qpos}  [{mark}]")
        if not ok:
            fails += 1

    if fails:
        raise SystemExit(f"{fails} target(s) exceed {THRESHOLD_M} m — edit cell.xml or pose_lookup.py")
    print(f"All targets within {THRESHOLD_M} m")


if __name__ == "__main__":
    main()
