"""Ground-truth part metadata for Phase 1 planning (color sorting, etc.)."""

from __future__ import annotations

PART_CATALOG: dict[str, dict[str, str]] = {
    "part_1": {"color": "yellow", "label": "yellow box", "shape": "box"},
    "part_2": {"color": "blue", "label": "blue box", "shape": "box"},
    "part_3": {"color": "green", "label": "green box", "shape": "box"},
}

# MuJoCo geom rgba per color (dashboard-visible sorting cues)
BOX_RGBA: dict[str, list[float]] = {
    "yellow": [0.95, 0.85, 0.15, 1.0],
    "blue": [0.25, 0.45, 0.92, 1.0],
    "green": [0.22, 0.72, 0.38, 1.0],
    "unknown": [0.75, 0.75, 0.75, 1.0],
}


def rgba_for_part(part_id: str) -> list[float]:
    color = PART_CATALOG.get(part_id, {}).get("color", "unknown")
    return BOX_RGBA.get(color, BOX_RGBA["unknown"])

TASK_BY_SCENARIO: dict[str, str] = {
    "default": "Pick all parts from bin_a and place them on station_1.",
    "sort_green": "Sort the green boxes to station_1.",
    "misaligned": "Parts in bin_a are misaligned — recover and complete placement at station_1.",
    "empty_bin": "Bin_a is empty — diagnose and complete the placement task if possible.",
}


def target_colors_for_task(task: str) -> list[str] | None:
    """Return color filter for sorting tasks, or None for all parts."""
    lower = task.lower()
    if "green" in lower:
        return ["green"]
    if "blue" in lower:
        return ["blue"]
    if "yellow" in lower:
        return ["yellow"]
    return None


def parts_for_task(parts: list[dict], task: str) -> list[dict]:
    colors = target_colors_for_task(task)
    if colors is None:
        return parts
    return [p for p in parts if p.get("color") in colors]


def is_task_done(parts: list[dict], task: str, scenario: str) -> bool:
    if scenario == "empty_bin":
        return False
    targets = parts_for_task(parts, task)
    if not targets:
        return False
    return all(p["at"] == "station_1" for p in targets)
