"""MCP server for the cell sim (stdio / HTTP).

Run:
    python -m factorymind.sim.a.mcp_server
    python -m factorymind.sim.a.mcp_server --http
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from factorymind.agent.schemas import CellPlan
from factorymind.sim.a.env_factory import get_cell_env
from factorymind.sim.a.targets import TARGET_POSES

mcp = FastMCP(
    "FactoryMind Sim",
    instructions=(
        "MuJoCo assembly cell simulator for FactoryMind. "
        "Use reset_cell before an episode, get_cell_state to read C2 state, "
        "and step_cell with a validated CellPlan (C1 schema). "
        "Named targets: bin_a, station_1, part_1/2/3, home."
    ),
)


@mcp.tool()
def reset_cell(seed: int = 0) -> dict[str, Any]:
    """Reset the cell to the initial pick-and-place scenario."""
    cell = get_cell_env()
    return cell.reset(seed)


@mcp.tool()
def get_cell_state() -> dict[str, Any]:
    """Return the current cell state (C2 schema): robots, parts, stations, events, done."""
    return get_cell_env().get_state()


@mcp.tool()
def step_cell(plan_json: str) -> dict[str, Any]:
    """Apply a CellPlan (C1) and advance the simulation one control step."""
    raw = json.loads(plan_json)
    plan = CellPlan.model_validate(raw)
    return get_cell_env().step(plan)


@mcp.tool()
def list_targets() -> list[str]:
    """List valid named targets for move/grip/release commands."""
    return get_cell_env().list_targets()


@mcp.tool()
def render_cell_frame(filename: str = "") -> str:
    """Save an offscreen PNG of the current cell (MuJoCo backend). Returns file path."""
    cell = get_cell_env()
    if not hasattr(cell, "save_frame"):
        return "Render requires FACTORYMIND_SIM_BACKEND=mujoco"
    path = cell.save_frame(filename or None)
    return str(path)


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
    parser.add_argument("--http", action="store_true", help="Use streamable HTTP transport")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port when --http")
    args = parser.parse_args()

    if args.http:
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
