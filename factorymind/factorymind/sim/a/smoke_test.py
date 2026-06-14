"""Smoke test for Role A sim — mock always; MuJoCo when installed."""

import os
import sys

from factorymind.sim.a.cell import MockCellEnv
from factorymind.sim.a.env_factory import create_cell_env
from factorymind.sim.a.oracle import run_oracle_episode


def _run_mock() -> None:
    env = MockCellEnv(num_robots=2, seed=0)
    final = run_oracle_episode(env)
    assert final["done"], f"Mock oracle failed: {final}"
    placed = sum(1 for p in final["parts"] if p["at"] == "station_1")
    print(f"OK [mock] — {final['step']} steps, {placed} parts at station_1")

    env_green = MockCellEnv(num_robots=2, seed=0, scenario="sort_green")
    final_green = run_oracle_episode(env_green)
    assert final_green["done"], f"Mock sort_green failed: {final_green}"
    green_placed = sum(
        1 for p in final_green["parts"] if p["color"] == "green" and p["at"] == "station_1"
    )
    print(f"OK [mock sort_green] — {final_green['step']} steps, {green_placed} green at station_1")

    env_mis = MockCellEnv(num_robots=2, seed=0, scenario="misaligned")
    final_mis = run_oracle_episode(env_mis)
    assert final_mis["done"], f"Mock misaligned failed: {final_mis}"
    placed_mis = sum(1 for p in final_mis["parts"] if p["at"] == "station_1")
    print(f"OK [mock misaligned] — {final_mis['step']} steps, {placed_mis} parts at station_1")

    env_cv = MockCellEnv(num_robots=2, seed=0, scenario="conveyor_feed")
    final_cv = run_oracle_episode(env_cv)
    assert final_cv["done"], f"Mock conveyor_feed failed: {final_cv}"
    placed_cv = sum(1 for p in final_cv["parts"] if p["id"].startswith("part_") and p["at"] == "station_1")
    print(f"OK [mock conveyor_feed] — {final_cv['step']} steps, {placed_cv} parts at station_1")


def _run_mujoco() -> None:
    os.environ["FACTORYMIND_SIM_BACKEND"] = "mujoco"
    env = create_cell_env()
    final = run_oracle_episode(env)
    assert final["done"], f"MuJoCo oracle failed: {final}"
    placed = sum(1 for p in final["parts"] if p["at"] == "station_1")
    print(f"OK [mujoco] — {final['step']} steps, {placed} parts at station_1")

    from factorymind.sim.a.config import SimConfig

    env_green = create_cell_env(SimConfig(backend="mujoco", scenario="sort_green", default_seed=0))
    final_green = run_oracle_episode(env_green)
    assert final_green["done"], f"MuJoCo sort_green failed: {final_green}"
    green_placed = sum(
        1 for p in final_green["parts"] if p["color"] == "green" and p["at"] == "station_1"
    )
    print(f"OK [mujoco sort_green] — {final_green['step']} steps, {green_placed} green at station_1")

    env_mis = create_cell_env(SimConfig(backend="mujoco", scenario="misaligned", default_seed=0))
    final_mis = run_oracle_episode(env_mis)
    assert final_mis["done"], f"MuJoCo misaligned failed: {final_mis}"
    placed_mis = sum(1 for p in final_mis["parts"] if p["at"] == "station_1")
    print(f"OK [mujoco misaligned] — {final_mis['step']} steps, {placed_mis} parts at station_1")

    env_cv = create_cell_env(SimConfig(backend="mujoco", scenario="conveyor_feed", default_seed=0))
    final_cv = run_oracle_episode(env_cv)
    assert final_cv["done"], f"MuJoCo conveyor_feed failed: {final_cv}"
    placed_cv = sum(1 for p in final_cv["parts"] if p["id"].startswith("part_") and p["at"] == "station_1")
    print(f"OK [mujoco conveyor_feed] — {final_cv['step']} steps, {placed_cv} parts at station_1")


def main() -> None:
    _run_mock()
    if os.environ.get("FACTORYMIND_SIM_SKIP_MUJOCO") == "1":
        return
    try:
        import mujoco  # noqa: F401
    except ImportError:
        print("SKIP [mujoco] — pip install mujoco to run physics smoke test")
        return
    try:
        _run_mujoco()
        _run_render()
    except Exception as exc:
        print(f"WARN [mujoco] — {exc}", file=sys.stderr)


def _run_render() -> None:
    import os

    os.environ["FACTORYMIND_SIM_BACKEND"] = "mujoco"
    from factorymind.sim.a.mujoco_cell import MujocoCellEnv

    try:
        env = MujocoCellEnv(seed=0)
        path = env.save_frame()
    except Exception as exc:
        name = type(exc).__name__
        if "CGLError" in name or "GL" in str(exc):
            print(f"SKIP [render] — no GL context ({name}); use viewer or set MUJOCO_GL=egl on Linux")
            return
        raise
    assert path.exists() and path.stat().st_size > 0
    print(f"OK [render] — {path}")


if __name__ == "__main__":
    main()
