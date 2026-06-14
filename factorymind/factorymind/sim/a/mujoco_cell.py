"""MuJoCo cell — implement here when the MJCF scene is ready.

Switch backend via config.py or FACTORYMIND_SIM_BACKEND=mujoco once this class exists.
"""

from __future__ import annotations

from typing import Any

from factorymind.agent.schemas import CellPlan


class MujocoCellEnv:
    """Placeholder until MJCF scene + pose lookup table are wired."""

    num_robots: int = 2

    def __init__(self, num_robots: int = 2, seed: int = 0) -> None:
        self.num_robots = num_robots
        self.seed = seed
        raise NotImplementedError(
            "MuJoCo cell not built yet. Edit factorymind/sim/a/mujoco_cell.py "
            "and factorymind/sim/a/assets/. Using mock backend for now."
        )

    def reset(self, seed: int | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def get_state(self) -> dict[str, Any]:
        raise NotImplementedError

    def step(self, plan: CellPlan) -> dict[str, Any]:
        raise NotImplementedError

    def list_targets(self) -> list[str]:
        raise NotImplementedError
