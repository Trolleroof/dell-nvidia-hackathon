"""Single entry point — create_cell_env() / get_cell_env()."""

from __future__ import annotations

from typing import Any

from factorymind.sim.a.cell import CellEnv, MockCellEnv
from factorymind.sim.a.config import SimConfig, get_config

_cell: CellEnv | None = None


def create_cell_env(config: SimConfig | None = None) -> CellEnv:
    """Build a fresh cell env (mock or mujoco per config)."""
    cfg = config or get_config()
    if cfg.backend == "mujoco":
        from factorymind.sim.a.mujoco_cell import MujocoCellEnv

        return MujocoCellEnv(num_robots=cfg.num_robots, seed=cfg.default_seed)
    return MockCellEnv(num_robots=cfg.num_robots, seed=cfg.default_seed)


def get_cell_env() -> CellEnv:
    """Singleton used by MCP server and local dev."""
    global _cell
    if _cell is None:
        _cell = create_cell_env()
    return _cell


def reset_cell_env(config: SimConfig | None = None) -> CellEnv:
    """Replace the singleton (e.g. after backend switch)."""
    global _cell
    _cell = create_cell_env(config)
    return _cell
