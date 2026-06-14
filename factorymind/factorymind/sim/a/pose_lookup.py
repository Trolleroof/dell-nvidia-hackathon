"""Derive joint targets from MJCF site positions — keeps poses in sync with cell.xml."""

from __future__ import annotations

from pathlib import Path

import mujoco

# arm{N}_base body origin in assets/cell.xml (world frame)
ARM_BASES: dict[int, tuple[float, float, float]] = {
    0: (0.15, 0.35, 0.44),
    1: (0.15, -0.15, 0.44),
}

# arm0_ee / arm1_ee sit 0.08 m below the z slide joint origin
EE_Z_OFFSET = 0.08

# Vertical approach offset (m) — lower for grip, default for hover
APPROACH_Z = {
    "default": 0.0,
    "part_1": -0.02,
    "part_2": -0.02,
    "part_3": -0.02,
}

HOME_QPOS_ARM0 = {"x": 0.05, "y": 0.0, "z": 0.12}
HOME_QPOS_ARM1 = {"x": 0.05, "y": 0.0, "z": 0.12}

SITE_TARGETS = (
    "bin_a",
    "bin_b",
    "station_1",
    "station_2",
    "part_1",
    "part_2",
    "part_3",
)


def scene_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "cell.xml"


def world_to_qpos(
    target_xyz: tuple[float, float, float],
    arm_id: int,
    z_delta: float = 0.0,
) -> dict[str, float]:
    """Convert a world-frame point to slide-joint values for one arm."""
    bx, by, bz = ARM_BASES[arm_id]
    tx, ty, tz = target_xyz
    tz_eff = tz + z_delta
    return {
        "x": round(tx - bx, 4),
        "y": round(ty - by, 4),
        "z": round(tz_eff + EE_Z_OFFSET - bz, 4),
    }


def _site_xyz(model: mujoco.MjModel, name: str) -> tuple[float, float, float]:
    sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)
    if sid < 0:
        raise KeyError(name)
    pos = model.site_pos[sid]
    return float(pos[0]), float(pos[1]), float(pos[2])


def build_qpos_tables(model: mujoco.MjModel | None = None) -> tuple[dict, dict]:
    """Build TARGET_QPOS (arm0) and TARGET_QPOS_ARM1 from world-frame site positions."""
    if model is None:
        model = mujoco.MjModel.from_xml_path(str(scene_path()))

    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    arm0: dict[str, dict[str, float]] = {"home": dict(HOME_QPOS_ARM0)}
    arm1: dict[str, dict[str, float]] = {"home": dict(HOME_QPOS_ARM1)}

    for name in SITE_TARGETS:
        if name.startswith("part_"):
            bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
            if bid < 0:
                continue
            pos = data.xpos[bid]
        else:
            sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)
            if sid < 0:
                continue
            pos = data.site_xpos[sid]
        xyz = float(pos[0]), float(pos[1]), float(pos[2])
        z_delta = APPROACH_Z.get(name, APPROACH_Z["default"])
        arm0[name] = world_to_qpos(xyz, arm_id=0, z_delta=z_delta)
        arm1[name] = world_to_qpos(xyz, arm_id=1, z_delta=z_delta)

    return arm0, arm1


def ee_distance_to_site(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    arm_id: int,
    site_name: str,
) -> float:
    """Euclidean distance (m) from end-effector to a named site."""
    ee_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"arm{arm_id}_ee")
    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    ee = data.site_xpos[ee_id]
    sp = data.site_xpos[site_id]
    return float(((ee - sp) ** 2).sum() ** 0.5)
