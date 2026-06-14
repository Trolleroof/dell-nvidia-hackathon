"""Named targets → pose labels and joint goals (from assets/poses.json)."""

from __future__ import annotations

import json
from pathlib import Path

TARGET_POSES: dict[str, str] = {
    "home": "home",
    "bin_a": "above_bin_a",
    "bin_b": "above_bin_b",
    "station_1": "above_station_1",
    "station_2": "above_station_2",
    "part_1": "above_part_1",
    "part_2": "above_part_2",
    "part_3": "above_part_3",
    "conveyor_pick": "above_conveyor_pick",
}

ARM_JOINT_NAMES = (
    "joint1",
    "joint2",
    "joint3",
    "joint4",
    "joint5",
    "joint6",
    "joint7",
)
HOME_QPOS = [0.0, 0.0, 0.0, -1.57079, 0.0, 1.57079, -0.7853]
POSES_PATH = Path(__file__).resolve().parent / "assets" / "poses.json"


def scene_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "cell.xml"


def _joint_dict(qpos_list: list[float]) -> dict[str, float]:
    return {
        name: round(float(qpos_list[i]), 6)
        for i, name in enumerate(ARM_JOINT_NAMES)
        if i < len(qpos_list)
    }


def _load_qpos_tables() -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    poses = json.loads(POSES_PATH.read_text())
    return (
        {name: _joint_dict(q) for name, q in poses["arm0"].items()},
        {name: _joint_dict(q) for name, q in poses["arm1"].items()},
    )


try:
    TARGET_QPOS, TARGET_QPOS_ARM1 = _load_qpos_tables()
except Exception:
    _home = _joint_dict(HOME_QPOS)
    TARGET_QPOS = {"home": dict(_home)}
    TARGET_QPOS_ARM1 = {"home": dict(_home)}

__all__ = ["TARGET_POSES", "TARGET_QPOS", "TARGET_QPOS_ARM1", "scene_path"]
