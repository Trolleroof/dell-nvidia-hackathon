"""C2 — Sim state types (owned by Role A)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from factorymind.sim.a.part_catalog import PART_CATALOG, TASK_BY_SCENARIO

GripperState = Literal["open", "closed"]
StationStatus = Literal["empty", "occupied", "done"]
PartLocation = str  # bin_a | station_1 | gripper_0 | ...
Scenario = Literal["default", "sort_green", "misaligned", "empty_bin"]


@dataclass
class RobotState:
    id: int
    pose: str
    gripper: GripperState
    holding: str | None


@dataclass
class PartState:
    id: str
    pos: list[float]
    at: PartLocation
    color: str = "unknown"
    label: str = ""
    shape: str = "box"

    @classmethod
    def from_id(cls, part_id: str, pos: list[float], at: PartLocation) -> PartState:
        meta = PART_CATALOG.get(part_id, {})
        return cls(
            id=part_id,
            pos=pos,
            at=at,
            color=meta.get("color", "unknown"),
            label=meta.get("label", part_id),
            shape=meta.get("shape", "box"),
        )


@dataclass
class StationState:
    id: str
    status: StationStatus


@dataclass
class CellState:
    step: int
    robots: list[RobotState]
    parts: list[PartState]
    stations: list[StationState]
    events: list[str]
    done: bool
    task: str = TASK_BY_SCENARIO["default"]
    scenario: Scenario = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "task": self.task,
            "scenario": self.scenario,
            "robots": [
                {
                    "id": r.id,
                    "pose": r.pose,
                    "gripper": r.gripper,
                    "holding": r.holding,
                }
                for r in self.robots
            ],
            "parts": [
                {
                    "id": p.id,
                    "pos": p.pos,
                    "at": p.at,
                    "color": p.color,
                    "label": p.label,
                    "shape": p.shape,
                }
                for p in self.parts
            ],
            "stations": [{"id": s.id, "status": s.status} for s in self.stations],
            "events": list(self.events),
            "done": self.done,
        }
