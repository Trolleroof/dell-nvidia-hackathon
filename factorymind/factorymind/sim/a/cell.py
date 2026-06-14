"""Mock cell environment — replace internals with MuJoCo in mujoco_cell.py when ready."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.a.part_catalog import TASK_BY_SCENARIO, is_task_done
from factorymind.sim.a.state import CellState, PartState, RobotState, Scenario, StationState
from factorymind.sim.a.targets import TARGET_POSES

MISALIGNED_OFFSETS = {
    "part_1": (0.06, 0.04, 0.0),
    "part_2": (0.05, -0.03, 0.0),
    "part_3": (-0.04, 0.05, 0.0),
}


class CellEnv(Protocol):
    """Stable sim interface — reset, state, step."""

    num_robots: int

    def reset(self, seed: int | None = None) -> dict[str, Any]: ...
    def get_state(self) -> dict[str, Any]: ...
    def step(self, plan: CellPlan) -> dict[str, Any]: ...
    def list_targets(self) -> list[str]: ...


@dataclass
class MockCellEnv:
    """Deterministic mock cell — no MuJoCo required.

    Two robots, one pick-and-place task: move parts from bin_a to station_1.
    """

    num_robots: int = 2
    seed: int = 0
    scenario: Scenario = "default"
    _rng: random.Random = field(init=False, repr=False)
    _step: int = field(default=0, init=False)
    _robots: list[RobotState] = field(default_factory=list, init=False)
    _parts: list[PartState] = field(default_factory=list, init=False)
    _stations: list[StationState] = field(default_factory=list, init=False)
    _events: list[str] = field(default_factory=list, init=False)
    _done: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self.reset(self.seed)

    def reset(self, seed: int | None = None) -> dict[str, Any]:
        if seed is not None:
            self.seed = seed
            self._rng = random.Random(seed)
        self._step = 0
        self._events = []
        self._done = False
        if self.scenario == "empty_bin":
            self._parts = []
            self._events.append("scenario_empty_bin")
        else:
            self._parts = []
            defaults = {
                "part_1": [0.1, 0.2, 0.05],
                "part_2": [0.15, 0.2, 0.05],
                "part_3": [0.2, 0.2, 0.05],
            }
            for part_id, pos in defaults.items():
                if self.scenario == "misaligned":
                    dx, dy, dz = MISALIGNED_OFFSETS.get(part_id, (0.0, 0.0, 0.0))
                    pos = [pos[0] + dx, pos[1] + dy, pos[2] + dz]
                self._parts.append(PartState.from_id(part_id, pos, "bin_a"))
            if self.scenario == "misaligned":
                self._events.append("scenario_misaligned")
        self._robots = [
            RobotState(id=i, pose="home", gripper="open", holding=None)
            for i in range(self.num_robots)
        ]
        self._stations = [
            StationState(id="station_1", status="empty"),
            StationState(id="station_2", status="empty"),
        ]
        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        return CellState(
            step=self._step,
            robots=self._robots,
            parts=self._parts,
            stations=self._stations,
            events=list(self._events),
            done=self._done,
            task=TASK_BY_SCENARIO.get(self.scenario, TASK_BY_SCENARIO["default"]),
            scenario=self.scenario,
        ).to_dict()

    def list_targets(self) -> list[str]:
        return sorted(TARGET_POSES.keys())

    def step(self, plan: CellPlan) -> dict[str, Any]:
        self._events = []
        self._step += 1

        for cmd in plan.robots:
            if cmd.id < 0 or cmd.id >= self.num_robots:
                self._events.append("invalid_robot_id")
                continue
            self._apply_command(cmd)

        task = TASK_BY_SCENARIO.get(self.scenario, TASK_BY_SCENARIO["default"])
        parts_dict = [
            {"id": p.id, "at": p.at, "color": p.color}
            for p in self._parts
        ]
        if self._parts and is_task_done(parts_dict, task, self.scenario):
            self._done = True
            if "task_complete" not in self._events:
                self._events.append("task_complete")

        return self.get_state()

    def _apply_command(self, cmd: RobotCommand) -> None:
        robot = self._robots[cmd.id]
        target = cmd.target

        if target not in TARGET_POSES and not target.startswith("part_"):
            self._events.append("invalid_target")
            return

        if cmd.action == "hold":
            return

        if cmd.action == "move":
            pose = TARGET_POSES.get(target, f"above_{target}")
            robot.pose = pose
            return

        if cmd.action == "grip":
            part = self._find_part(target)
            if part is None:
                self._events.append("grip_miss")
                return
            if robot.gripper == "closed":
                self._events.append("gripper_busy")
                return
            robot.gripper = "closed"
            robot.holding = part.id
            part.at = f"gripper_{cmd.id}"
            self._events.append("pick_success")
            return

        if cmd.action == "release":
            if robot.gripper != "closed" or robot.holding is None:
                self._events.append("release_empty")
                return
            part = self._find_part(robot.holding)
            if part is None:
                self._events.append("release_miss")
                return
            station = self._find_station(target)
            if station is None:
                self._events.append("invalid_release_target")
                return
            robot.gripper = "open"
            robot.holding = None
            part.at = station.id
            station.status = "occupied"
            self._events.append("place_success")

    def _find_part(self, ref: str) -> PartState | None:
        for part in self._parts:
            if part.id == ref or part.at == ref:
                return part
        return None

    def _find_station(self, ref: str) -> StationState | None:
        for station in self._stations:
            if station.id == ref:
                return station
        return None
