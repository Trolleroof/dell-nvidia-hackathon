"""Load precomputed Franka joint poses from assets/poses.json."""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np

ARM_JOINT_NAMES = (
    "joint1",
    "joint2",
    "joint3",
    "joint4",
    "joint5",
    "joint6",
    "joint7",
)

# Menagerie panda home keyframe (7 arm joints, radians)
HOME_QPOS = [0.0, 0.0, 0.0, -1.57079, 0.0, 1.57079, -0.7853]

APPROACH_Z: dict[str, float] = {
    "default": 0.0,
    "part_1": -0.02,
    "part_2": -0.02,
    "part_3": -0.02,
}

SITE_TARGETS = (
    "bin_a",
    "bin_b",
    "station_1",
    "station_2",
    "part_1",
    "part_2",
    "part_3",
)

POSES_PATH = Path(__file__).resolve().parent / "assets" / "poses.json"


def scene_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "cell.xml"


def _joint_dict(arm_id: int, qpos_list: list[float]) -> dict[str, float]:
    return {
        name: round(float(qpos_list[i]), 6)
        for i, name in enumerate(ARM_JOINT_NAMES)
        if i < len(qpos_list)
    }


def load_poses_json(path: Path | None = None) -> dict:
    p = path or POSES_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"Missing {p} — run: python -m factorymind.sim.a.solve_poses"
        )
    return json.loads(p.read_text())


def build_qpos_tables(
    model: mujoco.MjModel | None = None,
    poses: dict | None = None,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Return TARGET_QPOS tables for arm0 and arm1 from poses.json."""
    if poses is None:
        poses = load_poses_json()

    arm0 = {name: _joint_dict(0, q) for name, q in poses["arm0"].items()}
    arm1 = {name: _joint_dict(1, q) for name, q in poses["arm1"].items()}
    return arm0, arm1


def ee_distance_to_site(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    arm_id: int,
    site_name: str,
) -> float:
    """Euclidean distance (m) from end-effector to a named site/body."""
    ee_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"arm{arm_id}_ee")
    ee = data.site_xpos[ee_id]
    if site_name.startswith("part_"):
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, site_name)
        tgt = data.xpos[bid]
    else:
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
        tgt = data.site_xpos[sid]
    return float(np.linalg.norm(ee - tgt))


def apply_arm_qpos(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    arm_id: int,
    qpos: dict[str, float],
    *,
    gripper_open: bool = True,
) -> None:
    """Set arm joint positions (and optional gripper width)."""
    for jname, val in qpos.items():
        full = f"arm{arm_id}_{jname}"
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, full)
        if jid < 0:
            continue
        adr = int(model.jnt_qposadr[jid])
        data.qpos[adr] = val
        idx = int(jname.replace("joint", ""))
        act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"arm{arm_id}_actuator{idx}")
        if act >= 0:
            data.ctrl[act] = val
    finger = 0.04 if gripper_open else 0.0
    for fj in (1, 2):
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"arm{arm_id}_finger_joint{fj}")
        if jid >= 0:
            data.qpos[int(model.jnt_qposadr[jid])] = finger
    mujoco.mj_forward(model, data)


def read_arm_qpos(model: mujoco.MjModel, data: mujoco.MjData, arm_id: int) -> dict[str, float]:
    out: dict[str, float] = {}
    for jname in ARM_JOINT_NAMES:
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"arm{arm_id}_{jname}")
        if jid >= 0:
            out[jname] = float(data.qpos[int(model.jnt_qposadr[jid])])
    return out
