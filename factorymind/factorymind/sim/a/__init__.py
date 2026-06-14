"""Role A (Simulation Engineer) workspace — edit files here only.

Other roles should import from this package, not duplicate sim logic:
    from factorymind.sim.a import create_cell_env, get_cell_env
"""

from factorymind.sim.a.cell import MockCellEnv
from factorymind.sim.a.config import SimConfig, get_config
from factorymind.sim.a.env_factory import create_cell_env, get_cell_env
from factorymind.sim.a.state import CellState, PartState, RobotState, StationState
from factorymind.sim.a.targets import TARGET_POSES

__all__ = [
    "CellState",
    "MockCellEnv",
    "PartState",
    "RobotState",
    "SimConfig",
    "StationState",
    "TARGET_POSES",
    "create_cell_env",
    "get_cell_env",
    "get_config",
]
