"""Deterministic oracle policy — completes the pick-and-place without an LLM."""

from __future__ import annotations

from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.a.cell import CellEnv
from factorymind.sim.a.part_catalog import parts_for_task
from factorymind.sim.a.targets import TARGET_POSES


def _hold_r1() -> RobotCommand:
    return RobotCommand(id=1, action="hold", target="home", reason="Stand clear of robot 0's work zone.")


def _approach_target(part_id: str, scenario: str, events: list[str]) -> str:
    """Misaligned parts (or a missed grip) need per-part approach, not bin center."""
    if scenario == "misaligned" or "grip_miss" in events:
        return part_id
    return "bin_a"


def _expected_pose(target: str) -> str:
    return TARGET_POSES.get(target, f"above_{target}")


def oracle_plan(state: dict) -> CellPlan:
    """Return the next correct CellPlan for the pick-and-place task."""
    robots = state["robots"]
    parts = state["parts"]
    task = state.get("task", "")
    scenario = state.get("scenario", "default")
    events = state.get("events", [])
    pending = [p for p in parts_for_task(parts, task) if p["at"] == "bin_a"]
    in_gripper = [p for p in parts_for_task(parts, task) if p["at"].startswith("gripper_")]

    r0 = next(r for r in robots if r["id"] == 0)

    if r0["holding"]:
        if r0["pose"] == "above_station_1":
            return CellPlan(
                plan="Robot 0 releases at station_1 after positioning.",
                robots=[
                    RobotCommand(
                        id=0,
                        action="release",
                        target="station_1",
                        reason="Deposit the part on the station fixture.",
                    ),
                    _hold_r1(),
                ],
            )
        return CellPlan(
            plan="Robot 0 carries part to station_1 and releases.",
            robots=[
                RobotCommand(
                    id=0,
                    action="move",
                    target="station_1",
                    reason="Approach the assembly station with the held part.",
                ),
                _hold_r1(),
            ],
        )

    if r0["gripper"] == "closed" and r0["holding"] is None:
        return CellPlan(
            plan="Robot 0 releases at station_1 after positioning.",
            robots=[
                RobotCommand(
                    id=0,
                    action="release",
                    target="station_1",
                    reason="Deposit the part on the station fixture.",
                ),
                _hold_r1(),
            ],
        )

    if pending and r0["gripper"] == "open":
        part_id = pending[0]["id"]
        approach = _approach_target(part_id, scenario, events)
        approach_pose = _expected_pose(approach)

        if r0["pose"] != approach_pose:
            reason = (
                f"Re-align over {part_id} after misalignment — approach the part directly."
                if scenario == "misaligned" or "grip_miss" in events
                else f"Position over {approach} before gripping {part_id}."
            )
            return CellPlan(
                plan=f"Robot 0 moves to {approach} to pick {part_id}.",
                robots=[
                    RobotCommand(id=0, action="move", target=approach, reason=reason),
                    _hold_r1(),
                ],
            )

        return CellPlan(
            plan=f"Robot 0 grips {part_id} from bin_a.",
            robots=[
                RobotCommand(
                    id=0,
                    action="grip",
                    target=part_id,
                    reason=f"Close gripper on {part_id} once aligned.",
                ),
                RobotCommand(
                    id=1,
                    action="hold",
                    target="home",
                    reason="No concurrent action required on robot 1 this step.",
                ),
            ],
        )

    if in_gripper:
        return CellPlan(
            plan="Robot 0 finishes placement at station_1.",
            robots=[
                RobotCommand(
                    id=0,
                    action="release",
                    target="station_1",
                    reason="Complete placement for part currently in gripper.",
                ),
                _hold_r1(),
            ],
        )

    return CellPlan(
        plan="All parts placed — hold position.",
        robots=[
            RobotCommand(id=0, action="hold", target="home", reason="Task complete."),
            RobotCommand(id=1, action="hold", target="home", reason="Task complete."),
        ],
    )


def run_oracle_episode(env: CellEnv, max_steps: int = 50) -> dict:
    """Run the cell to completion using the oracle policy."""
    env.reset(0)
    for _ in range(max_steps):
        state = env.get_state()
        if state["done"]:
            break
        plan = oracle_plan(state)
        env.step(plan)
    return env.get_state()
