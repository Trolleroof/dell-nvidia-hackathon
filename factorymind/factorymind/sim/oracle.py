"""Deterministic oracle policy — completes the pick-and-place without an LLM."""

from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.mock_cell import MockCellEnv


def oracle_plan(state: dict) -> CellPlan:
    """Return the next correct CellPlan for the mock pick-and-place task."""
    robots = state["robots"]
    parts = state["parts"]
    pending = [p for p in parts if p["at"] == "bin_a"]
    in_gripper = [p for p in parts if p["at"].startswith("gripper_")]

    # Robot 0 picks from bin, robot 1 is backup / holds
    r0 = next(r for r in robots if r["id"] == 0)
    r1 = next(r for r in robots if r["id"] == 1)

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
                    RobotCommand(
                        id=1,
                        action="hold",
                        target="home",
                        reason="Remain clear of the placement zone.",
                    ),
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
                RobotCommand(
                    id=1,
                    action="hold",
                    target="home",
                    reason="Stand by at home while robot 0 places the part.",
                ),
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
                RobotCommand(
                    id=1,
                    action="hold",
                    target="home",
                    reason="Remain clear of the placement zone.",
                ),
            ],
        )

    if r0["pose"] != "above_bin_a" and pending:
        return CellPlan(
            plan="Robot 0 moves above bin_a to begin the next pick cycle.",
            robots=[
                RobotCommand(
                    id=0,
                    action="move",
                    target="bin_a",
                    reason="Position over the source bin for gripping.",
                ),
                RobotCommand(
                    id=1,
                    action="hold",
                    target="home",
                    reason="Idle at home until needed for a second parallel task.",
                ),
            ],
        )

    if pending and r0["gripper"] == "open":
        part_id = pending[0]["id"]
        return CellPlan(
            plan=f"Robot 0 grips {part_id} from bin_a.",
            robots=[
                RobotCommand(
                    id=0,
                    action="grip",
                    target=part_id,
                    reason=f"Close gripper on {part_id} once aligned over bin_a.",
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
                RobotCommand(
                    id=1,
                    action="hold",
                    target="home",
                    reason="Hold position while robot 0 completes the place.",
                ),
            ],
        )

    return CellPlan(
        plan="All parts placed — hold position.",
        robots=[
            RobotCommand(id=0, action="hold", target="home", reason="Task complete."),
            RobotCommand(id=1, action="hold", target="home", reason="Task complete."),
        ],
    )


def run_oracle_episode(env: MockCellEnv, max_steps: int = 50) -> dict:
    """Run the cell to completion using the oracle policy."""
    env.reset(0)
    for _ in range(max_steps):
        state = env.get_state()
        if state["done"]:
            break
        plan = oracle_plan(state)
        env.step(plan)
    return env.get_state()
