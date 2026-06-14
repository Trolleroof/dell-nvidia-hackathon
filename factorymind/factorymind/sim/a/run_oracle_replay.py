"""Run oracle episode and save a PNG per step (demo replay).

    python -m factorymind.sim.a.run_oracle_replay
"""

from __future__ import annotations

from factorymind.sim.a.mujoco_cell import MujocoCellEnv
from factorymind.sim.a.oracle import oracle_plan


def main() -> None:
    env = MujocoCellEnv(seed=0)
    env.reset(0)

    try:
        env.save_frame("replay/step_0000.png")
    except Exception as exc:
        print(f"Render unavailable: {exc}")

    for step in range(1, 51):
        state = env.get_state()
        if state["done"]:
            break
        plan = oracle_plan(state)
        env.step(plan)
        try:
            env.save_frame(f"replay/step_{step:04d}.png")
        except Exception as exc:
            print(f"Frame skip at step {step}: {exc}")
            break

    final = env.get_state()
    frame_dir = env._frames_dir / "replay"
    n_frames = len(list(frame_dir.glob("*.png"))) if frame_dir.exists() else 0
    print(f"Replay done — {final['step']} steps, done={final['done']}, {n_frames} frames")
    print(f"Frames: {frame_dir}")


if __name__ == "__main__":
    main()
