"""Named targets → pose labels and joint goals (from assets/poses.json)."""

from __future__ import annotations

from factorymind.sim.a.pose_lookup import build_qpos_tables, scene_path

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

try:
    TARGET_QPOS, TARGET_QPOS_ARM1 = build_qpos_tables()
except Exception:
    _home = {f"joint{i}": v for i, v in enumerate(
        [0.0, 0.0, 0.0, -1.57079, 0.0, 1.57079, -0.7853], start=1
    )}
    TARGET_QPOS = {"home": dict(_home)}
    TARGET_QPOS_ARM1 = {"home": dict(_home)}

__all__ = ["TARGET_POSES", "TARGET_QPOS", "TARGET_QPOS_ARM1", "scene_path"]
