"""C1 — Action schema (co-owned by Sim + Agent)."""

from typing import Literal

from pydantic import BaseModel, Field


class RobotCommand(BaseModel):
    id: int = Field(ge=0, description="Robot index, 0..N-1")
    action: Literal["move", "grip", "release", "hold"]
    target: str = Field(description='Named target, e.g. "bin_a", "station_1", "part_3"')
    reason: str = Field(default="", description="Short rationale for this robot's action")


class CellPlan(BaseModel):
    plan: str = Field(description="One-line cell-level intent")
    robots: list[RobotCommand] = Field(description="One entry per robot")
