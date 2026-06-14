"""Named targets → pose labels and joint goals (auto-derived from cell.xml)."""

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
}

# Built from MJCF site positions when cell.xml is present; static fallback otherwise.
try:
    TARGET_QPOS, TARGET_QPOS_ARM1 = build_qpos_tables()
except Exception:
    TARGET_QPOS = {
        "home": {"x": 0.05, "y": 0.0, "z": 0.12},
        "bin_a": {"x": 0.10, "y": -0.20, "z": 0.08},
        "bin_b": {"x": 0.10, "y": -0.10, "z": 0.08},
        "station_1": {"x": 0.60, "y": -0.20, "z": 0.08},
        "station_2": {"x": 0.60, "y": -0.10, "z": 0.08},
        "part_1": {"x": 0.07, "y": -0.23, "z": 0.06},
        "part_2": {"x": 0.10, "y": -0.20, "z": 0.06},
        "part_3": {"x": 0.13, "y": -0.17, "z": 0.06},
    }
    TARGET_QPOS_ARM1 = {
        name: {"x": q["x"], "y": q["y"] + 0.50, "z": q["z"]}
        for name, q in TARGET_QPOS.items()
    }

__all__ = ["TARGET_POSES", "TARGET_QPOS", "TARGET_QPOS_ARM1", "scene_path"]
