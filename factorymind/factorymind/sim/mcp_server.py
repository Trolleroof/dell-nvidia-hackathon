"""MCP server exposing the FactoryMind cell sim to agents and Cursor.

Run (stdio — for Cursor / Claude Desktop):
    python -m factorymind.sim.mcp_server

Run (HTTP — for NemoClaw / remote clients):
    python -m factorymind.sim.mcp_server --http
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from factorymind.agent.schemas import CellPlan
from factorymind.sim.mock_cell import MockCellEnv, TARGET_POSES

mcp = FastMCP(
    "FactoryMind Sim",
    instructions=(
        "MuJoCo assembly cell simulator for FactoryMind. "
        "Use reset_cell before an episode, get_cell_state to read C2 state, "
        "and step_cell with a validated CellPlan (C1 schema). "
        "Named targets: bin_a, station_1, part_1/2/3, home."
    ),
)

# Single in-process cell instance (MCP is one client at a time for the demo)
_cell = MockCellEnv(num_robots=2, seed=0)


@mcp.tool()
def reset_cell(seed: int = 0) -> dict[str, Any]:
    """Reset the cell to the initial pick-and-place scenario.

    Args:
        seed: Random seed for deterministic physics (mock uses this for reproducibility).
    """
    return _cell.reset(seed)


@mcp.tool()
def get_cell_state() -> dict[str, Any]:
    """Return the current cell state (C2 schema): robots, parts, stations, events, done."""
    return _cell.get_state()


@mcp.tool()
def step_cell(plan_json: str) -> dict[str, Any]:
    """Apply a CellPlan (C1) and advance the simulation one control step.

    Args:
        plan_json: JSON string matching CellPlan schema with `plan` and `robots` fields.
    """
    raw = json.loads(plan_json)
    plan = CellPlan.model_validate(raw)
    return _cell.step(plan)


@mcp.tool()
def list_targets() -> list[str]:
    """List valid named targets for move/grip/release commands."""
    return _cell.list_targets()


@mcp.resource("factorymind://schema/c2")
def state_schema() -> str:
    """C2 sim-state JSON schema reference."""
    return json.dumps(
        {
            "step": 42,
            "robots": [
                {
                    "id": 0,
                    "pose": "home",
                    "gripper": "open|closed",
                    "holding": "part_3|null",
                }
            ],
            "parts": [{"id": "part_3", "pos": [0, 0, 0], "at": "bin_a|station_1|gripper_0|..."}],
            "stations": [{"id": "station_1", "status": "empty|occupied|done"}],
            "events": ["pick_success", "collision", "task_complete"],
            "done": False,
        },
        indent=2,
    )


@mcp.resource("factorymind://schema/c1")
def action_schema() -> str:
    """C1 CellPlan JSON schema reference."""
    return json.dumps(CellPlan.model_json_schema(), indent=2)


@mcp.resource("factorymind://targets")
def target_lookup() -> str:
    """Named target → pose lookup table."""
    return json.dumps(TARGET_POSES, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="FactoryMind sim MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use streamable HTTP transport (default: stdio for Cursor)",
    )
    parser.add_argument("--port", type=int, default=8765, help="HTTP port when --http")
    args = parser.parse_args()

    if args.http:
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
