"""C2 — Sim state types (owned by Role A)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

GripperState = Literal["open", "closed"]
StationStatus = Literal["empty", "occupied", "done"]
PartLocation = str  # bin_a | station_1 | gripper_0 | ...


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "robots": [
                {
                    "id": r.id,
                    "pose": r.pose,
                    "gripper": r.gripper,
                    "holding": r.holding,
                }
                for r in self.robots
            ],
            "parts": [{"id": p.id, "pos": p.pos, "at": p.at} for p in self.parts],
            "stations": [{"id": s.id, "status": s.status} for s in self.stations],
            "events": list(self.events),
            "done": self.done,
        }
