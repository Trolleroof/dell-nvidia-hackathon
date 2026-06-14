"""Offline damped-least-squares IK — writes assets/poses.json from cell.xml sites."""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np

from factorymind.sim.a.build_cell import PART_DEFAULTS
from factorymind.sim.a.pose_lookup import (
    ARM_JOINT_NAMES,
    APPROACH_Z,
    HOME_QPOS,
    POSES_PATH,
    SITE_TARGETS,
    scene_path,
)

ARM0_TARGETS = ("bin_a", "station_1", "part_1", "part_2", "part_3", "conveyor_pick")
ARM1_TARGETS = ("bin_b", "station_2")

MAX_ITER = 300
POS_TOL = 0.002
LAMBDA = 0.05
STEP_SCALE = 0.5


def _arm_joint_ids(model: mujoco.MjModel, arm_id: int) -> tuple[list[int], list[int], list[int]]:
    """Return (joint_ids, qpos_adrs, dof_ids) for the 7 arm joints."""
    joint_ids: list[int] = []
    qpos_adrs: list[int] = []
    dof_ids: list[int] = []
    for jname in ARM_JOINT_NAMES:
        full = f"arm{arm_id}_{jname}"
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, full)
        if jid < 0:
            raise KeyError(f"Missing joint {full}")
        joint_ids.append(jid)
        qpos_adrs.append(int(model.jnt_qposadr[jid]))
        dof_ids.append(int(model.jnt_dofadr[jid]))
    return joint_ids, qpos_adrs, dof_ids


def _set_arm_qpos(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    arm_id: int,
    qpos: np.ndarray,
    qpos_adrs: list[int],
) -> None:
    for adr, val in zip(qpos_adrs, qpos):
        data.qpos[adr] = val
    for j in (1, 2):
        fj = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"arm{arm_id}_finger_joint{j}")
        if fj >= 0:
            data.qpos[int(model.jnt_qposadr[fj])] = 0.04
    mujoco.mj_forward(model, data)


def _clamp_to_limits(model: mujoco.MjModel, joint_ids: list[int], qpos: np.ndarray) -> np.ndarray:
    out = qpos.copy()
    for i, jid in enumerate(joint_ids):
        lo, hi = model.jnt_range[jid]
        if lo < hi:
            out[i] = float(np.clip(out[i], lo, hi))
    return out


def solve_position_ik(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    arm_id: int,
    target_xyz: np.ndarray,
    q0: np.ndarray | None = None,
) -> np.ndarray:
    """Position-only IK for one Franka arm. Returns 7 joint angles."""
    joint_ids, qpos_adrs, dof_ids = _arm_joint_ids(model, arm_id)
    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"arm{arm_id}_ee")

    q = np.array(HOME_QPOS if q0 is None else q0, dtype=float)
    _set_arm_qpos(model, data, arm_id, q, qpos_adrs)

    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))

    for _ in range(MAX_ITER):
        mujoco.mj_forward(model, data)
        ee = data.site_xpos[site_id]
        err = target_xyz - ee
        if float(np.linalg.norm(err)) < POS_TOL:
            break

        mujoco.mj_jacSite(model, data, jacp, jacr, site_id)
        J = jacp[:, dof_ids]
        dq = J.T @ np.linalg.solve(J @ J.T + LAMBDA**2 * np.eye(3), err)
        q = _clamp_to_limits(model, joint_ids, q + STEP_SCALE * dq)
        _set_arm_qpos(model, data, arm_id, q, qpos_adrs)

    return q


def _target_xyz(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    name: str,
) -> np.ndarray:
    if name.startswith("part_"):
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        pos = data.xpos[bid]
    else:
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)
        pos = data.site_xpos[sid]
    return np.array(pos, dtype=float)


def build_poses(model: mujoco.MjModel | None = None) -> dict:
    if model is None:
        model = mujoco.MjModel.from_xml_path(str(scene_path()))
    data = mujoco.MjData(model)

    for part_id, pos in PART_DEFAULTS.items():
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, part_id)
        jnt_adr = model.body_jntadr[bid]
        if jnt_adr >= 0:
            qadr = int(model.jnt_qposadr[jnt_adr])
            data.qpos[qadr : qadr + 3] = pos
    mujoco.mj_forward(model, data)

    poses: dict[str, dict[str, list[float]]] = {"arm0": {}, "arm1": {}}

    for arm_key, arm_id in (("arm0", 0), ("arm1", 1)):
        q_home = np.array(HOME_QPOS, dtype=float)
        poses[arm_key]["home"] = [round(float(v), 6) for v in q_home]

        q_seed = q_home.copy()
        for name in SITE_TARGETS:
            xyz = _target_xyz(model, data, name)
            z_delta = APPROACH_Z.get(name, APPROACH_Z["default"])
            target = xyz + np.array([0.0, 0.0, z_delta])
            q = solve_position_ik(model, data, arm_id, target, q0=q_seed)
            poses[arm_key][name] = [round(float(v), 6) for v in q]
            q_seed = q.copy()

    return poses


def ee_distance(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    arm_id: int,
    target_name: str,
    qpos: list[float],
) -> float:
    _, qpos_adrs, _ = _arm_joint_ids(model, arm_id)
    _set_arm_qpos(model, data, arm_id, np.array(qpos), qpos_adrs)
    ee_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"arm{arm_id}_ee")
    if target_name.startswith("part_"):
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, target_name)
        tgt = data.xpos[bid]
    else:
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, target_name)
        tgt = data.site_xpos[sid]
    ee = data.site_xpos[ee_id]
    return float(np.linalg.norm(ee - tgt))


def main() -> None:
    path = scene_path()
    if not path.exists():
        raise FileNotFoundError(f"Run build_cell first — missing {path}")

    model = mujoco.MjModel.from_xml_path(str(path))
    poses = build_poses(model)

    POSES_PATH.parent.mkdir(parents=True, exist_ok=True)
    POSES_PATH.write_text(json.dumps(poses, indent=2) + "\n")
    print(f"Wrote {POSES_PATH}")

    data = mujoco.MjData(model)
    fails = 0
    checks = [
        (0, ARM0_TARGETS, poses["arm0"]),
        (1, ("bin_b", "station_2"), poses["arm1"]),
    ]
    for arm_id, names, table in checks:
        for name in names:
            q = table[name]
            dist = ee_distance(model, data, arm_id, name, q)
            ok = dist <= (0.04 if name.startswith("part_") else 0.05)
            mark = "OK" if ok else "FAIL"
            print(f"  arm{arm_id} {name:<12} {dist:.4f} m  [{mark}]")
            if not ok:
                fails += 1

    if fails:
        raise SystemExit(f"{fails} target(s) exceed reach threshold after IK")
    print("All arm0 targets within threshold")


if __name__ == "__main__":
    main()
