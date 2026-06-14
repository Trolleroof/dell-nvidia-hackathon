"""MCP server for Role A sim — lives in sim/a/ to avoid merge conflicts.

Run (stdio — for Cursor / Claude Desktop):
    python -m factorymind.sim.a.mcp_server

Run (HTTP — for NemoClaw / OpenClaw remote clients):
    python -m factorymind.sim.a.mcp_server --http --port 8765
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
        "Workflow: set_task → reset_cell → loop(get_cell_state → step_cell) until done. "
        "Named targets: bin_a, bin_b, station_1, station_2, part_1/2/3, home."
    ),
)

# UI Prompt — task instruction set by the agent or user before an episode
_current_task: str = "Move all parts from bin_a to station_1."


# ── UI Prompt tools ────────────────────────────────────────────────────────────

@mcp.tool()
def set_task(instruction: str) -> dict[str, str]:
    """Set the current task instruction (UI Prompt).

    Args:
        instruction: Natural-language description of what the cell should accomplish.
                     Example: "Move all parts from bin_a to station_1."
    """
    global _current_task
    _current_task = instruction.strip()
    return {"status": "ok", "task": _current_task}


@mcp.tool()
def get_task() -> dict[str, str]:
    """Return the current task instruction (UI Prompt)."""
    return {"task": _current_task}


# ── Sim state tools ───────────────────────────────────────────────────────────

@mcp.tool()
def reset_cell(seed: int = 0) -> dict[str, Any]:
    """Reset the cell to the initial pick-and-place scenario.

    Args:
        seed: Random seed for deterministic physics.
    """
    cell = get_cell_env()
    return cell.reset(seed)


@mcp.tool()
def get_cell_state() -> dict[str, Any]:
    """Return the current cell state (C2 schema).

    Returns a structured snapshot with four named sections matching the
    MCP architecture — object_states, environment_state, robot_arm_states —
    plus the active task instruction and flat C2 fields for backward compat.
    """
    raw = get_cell_env().get_state()

    # Architecture-aligned sections (object states / environment / robot arms)
    mujoco_state = {
        "robot_arm_states": raw["robots"],
        "object_states": raw["parts"],
        "environment_state": {
            "stations": raw["stations"],
            "step": raw["step"],
            "done": raw["done"],
            "events": raw["events"],
        },
    }

    return {
        # Architecture sections
        "mujoco_state": mujoco_state,
        "ui_prompt": {"task": _current_task},
        # Flat C2 fields — kept for backward compat with B's loop
        **raw,
    }


@mcp.tool()
def step_cell(plan_json: str) -> dict[str, Any]:
    """Apply a CellPlan (C1) and advance the simulation one control step.

    Args:
        plan_json: JSON string matching CellPlan schema (plan + robots fields).
    """
    raw = json.loads(plan_json)
    plan = CellPlan.model_validate(raw)
    result = get_cell_env().step(plan)

    # Return with architecture sections, same as get_cell_state
    mujoco_state = {
        "robot_arm_states": result["robots"],
        "object_states": result["parts"],
        "environment_state": {
            "stations": result["stations"],
            "step": result["step"],
            "done": result["done"],
            "events": result["events"],
        },
    }
    return {
        "mujoco_state": mujoco_state,
        "ui_prompt": {"task": _current_task},
        **result,
    }


@mcp.tool()
def list_targets() -> list[str]:
    """List valid named targets for move/grip/release commands."""
    return get_cell_env().list_targets()


# ── Resources (schema references) ─────────────────────────────────────────────

@mcp.resource("factorymind://schema/c2")
def state_schema() -> str:
    """C2 sim-state JSON schema reference — includes architecture sections."""
    return json.dumps(
        {
            "mujoco_state": {
                "robot_arm_states": [
                    {"id": 0, "pose": "home", "gripper": "open|closed", "holding": "part_3|null"}
                ],
                "object_states": [
                    {"id": "part_3", "pos": [0, 0, 0], "at": "bin_a|station_1|gripper_0|..."}
                ],
                "environment_state": {
                    "stations": [{"id": "station_1", "status": "empty|occupied|done"}],
                    "step": 42,
                    "done": False,
                    "events": ["pick_success", "collision", "task_complete"],
                },
            },
            "ui_prompt": {"task": "Move all parts from bin_a to station_1."},
            "step": 42,
            "robots": "...(same as robot_arm_states, flat compat)",
            "parts": "...(same as object_states, flat compat)",
            "stations": "...(same as environment_state.stations, flat compat)",
            "events": ["pick_success"],
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


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="FactoryMind sim MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use streamable HTTP transport (default: stdio for Cursor/Claude Desktop)",
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
