"""Deterministic oracle policy — completes the pick-and-place without an LLM."""

from __future__ import annotations

from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.a.cell import CellEnv
from factorymind.sim.a.conveyor import part_at_pick_zone
from factorymind.sim.a.part_catalog import parts_for_task, target_station_for_task
from factorymind.sim.a.targets import TARGET_POSES


def _hold_r1() -> RobotCommand:
    return RobotCommand(id=1, action="hold", target="home", reason="Stand clear of robot 0's work zone.")


def _pick_source(scenario: str) -> str:
    return "conveyor" if scenario == "conveyor_feed" else "bin_a"


def _approach_target(part_id: str, scenario: str, events: list[str]) -> str:
    """Approach the specific part so the pickup is physically visible."""
    if scenario == "conveyor_feed":
        return "conveyor_pick"
    return part_id


def _expected_pose(target: str) -> str:
    return TARGET_POSES.get(target, f"above_{target}")


def _part_ready_at_pick(part: dict, scenario: str) -> bool:
    if scenario != "conveyor_feed":
        return True
    pos = part.get("pos") or []
    if len(pos) < 1:
        return False
    return part_at_pick_zone(float(pos[0]))


def oracle_plan(state: dict) -> CellPlan:
    """Return the next correct CellPlan for the pick-and-place task."""
    robots = state["robots"]
    parts = state["parts"]
    task = state.get("task", "")
    scenario = state.get("scenario", "default")
    events = state.get("events", [])
    pick_source = _pick_source(scenario)
    station = target_station_for_task(task)
    station_pose = _expected_pose(station)
    pending = [p for p in parts_for_task(parts, task) if p["at"] == pick_source]
    in_gripper = [p for p in parts_for_task(parts, task) if p["at"].startswith("gripper_")]

    r0 = next(r for r in robots if r["id"] == 0)

    if r0["holding"]:
        if r0["pose"] == station_pose:
            return CellPlan(
                plan="Robot 0 releases at target station after positioning.",
                robots=[
                    RobotCommand(
                        id=0,
                        action="release",
                        target=station,
                        reason="Deposit the part on the requested station fixture.",
                    ),
                    _hold_r1(),
                ],
            )
        return CellPlan(
            plan="Robot 0 carries part to target station and releases.",
            robots=[
                RobotCommand(
                    id=0,
                    action="move",
                    target=station,
                    reason="Approach the requested assembly station with the held part.",
                ),
                _hold_r1(),
            ],
        )

    if r0["gripper"] == "closed" and r0["holding"] is None:
        return CellPlan(
            plan="Robot 0 releases at target station after positioning.",
            robots=[
                RobotCommand(
                    id=0,
                    action="release",
                    target=station,
                    reason="Deposit the part on the requested station fixture.",
                ),
                _hold_r1(),
            ],
        )

    if pending and r0["gripper"] == "open":
        approach = _approach_target(pending[0]["id"], scenario, events)
        approach_pose = _expected_pose(approach)

        if scenario == "conveyor_feed":
            ready = [p for p in pending if _part_ready_at_pick(p, scenario)]
            if r0["pose"] != approach_pose:
                return CellPlan(
                    plan="Robot 0 moves to conveyor_pick to receive the next part.",
                    robots=[
                        RobotCommand(
                            id=0,
                            action="move",
                            target="conveyor_pick",
                            reason="Position at the pick station along the belt.",
                        ),
                        _hold_r1(),
                    ],
                )
            if not ready:
                return CellPlan(
                    plan="Robot 0 waits at conveyor_pick for the next part.",
                    robots=[
                        RobotCommand(
                            id=0,
                            action="hold",
                            target="conveyor_pick",
                            reason="Belt is advancing — wait until a part reaches the pick zone.",
                        ),
                        _hold_r1(),
                    ],
                )
            part_id = ready[0]["id"]
            return CellPlan(
                plan=f"Robot 0 grips {part_id} from the conveyor.",
                robots=[
                    RobotCommand(
                        id=0,
                        action="grip",
                        target=part_id,
                        reason=f"Close gripper on {part_id} at conveyor_pick.",
                    ),
                    RobotCommand(
                        id=1,
                        action="hold",
                        target="home",
                        reason="No concurrent action required on robot 1 this step.",
                    ),
                ],
            )

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
            plan="Robot 0 finishes placement at target station.",
            robots=[
                RobotCommand(
                    id=0,
                    action="release",
                    target=station,
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


def run_oracle_episode(env: CellEnv, max_steps: int | None = None) -> dict:
    """Run the cell to completion using the oracle policy."""
    if max_steps is None:
        scenario = getattr(env, "scenario", "default")
        max_steps = 160 if scenario == "conveyor_feed" else 50
    env.reset(0)
    for _ in range(max_steps):
        state = env.get_state()
        if state["done"]:
            break
        plan = oracle_plan(state)
        env.step(plan)
    return env.get_state()
