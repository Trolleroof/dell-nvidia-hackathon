"""Verify arm reaches each named target — run after editing cell.xml.

    python -m factorymind.sim.a.verify_poses
"""

from __future__ import annotations

import mujoco

from factorymind.sim.a.mujoco_cell import MujocoCellEnv
from factorymind.sim.a.pose_lookup import ee_distance_to_site
from factorymind.sim.a.targets import TARGET_QPOS, TARGET_QPOS_ARM1

THRESHOLD_M = 0.05
PART_THRESHOLD_M = 0.04

# arm0 covers +Y fixtures; arm1 covers -Y fixtures (dual-arm layout)
ARM0_TARGETS = ("bin_a", "station_1", "part_1", "part_2", "part_3")
ARM1_TARGETS = ("bin_b", "station_2")


def _check_target(
    env: MujocoCellEnv,
    arm_id: int,
    name: str,
    qpos: dict[str, float],
) -> tuple[float, bool]:
    model, data = env.model, env.data
    env.reset(0)
    env._move_arm(arm_id, qpos)
    mujoco.mj_forward(model, data)
    if name.startswith("part_"):
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        ee_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"arm{arm_id}_ee")
        ee = data.site_xpos[ee_id]
        bp = data.xpos[bid]
        dist = float(((ee - bp) ** 2).sum() ** 0.5)
        ok = dist <= PART_THRESHOLD_M
    else:
        dist = ee_distance_to_site(model, data, arm_id=arm_id, site_name=name)
        ok = dist <= THRESHOLD_M
    return dist, ok


def main() -> None:
    env = MujocoCellEnv(seed=0)
    fails = 0

    print(f"{'arm':<5} {'target':<12} {'dist_m':>8}  qpos")
    for name in ARM0_TARGETS:
        qpos = TARGET_QPOS.get(name)
        if qpos is None:
            print(f"arm0  {name:<12} {'SKIP':>8}  (no pose)")
            continue
        dist, ok = _check_target(env, 0, name, qpos)
        mark = "OK" if ok else "FAIL"
        print(f"arm0  {name:<12} {dist:8.4f}  {qpos}  [{mark}]")
        if not ok:
            fails += 1

    for name in ARM1_TARGETS:
        qpos = TARGET_QPOS_ARM1.get(name)
        if qpos is None:
            print(f"arm1  {name:<12} {'SKIP':>8}  (no pose)")
            continue
        dist, ok = _check_target(env, 1, name, qpos)
        mark = "OK" if ok else "FAIL"
        print(f"arm1  {name:<12} {dist:8.4f}  {qpos}  [{mark}]")
        if not ok:
            fails += 1

    if fails:
        raise SystemExit(f"{fails} target(s) exceed threshold — re-run solve_poses or edit cell.xml")
    print(f"All assigned targets within {THRESHOLD_M} m")


if __name__ == "__main__":
    main()
