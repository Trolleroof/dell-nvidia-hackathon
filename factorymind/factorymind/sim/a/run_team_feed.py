"""Run oracle episode and publish everything B/C need — no MuJoCo knowledge required.

Writes:
  - factorymind/telemetry/diffusion_run.jsonl  (isolated diffusion C5 rows)
  - factorymind/telemetry/ar_run.jsonl           (isolated AR C5 rows, matched precision)
  - factorymind/telemetry/run.jsonl              (alias → diffusion_run for live feed)
  - factorymind/telemetry/oracle_replay.jsonl    (diffusion copy for dashboard Replay)
  - sim/a/frames/replay/step_XXXX.png            (720p MuJoCo frames)
  - sim/a/frames/latest.png                      (dashboard poll target)

Usage:
    cd factorymind && source .venv/bin/activate
    export FACTORYMIND_SIM_BACKEND=mujoco
    python -m factorymind.sim.a.run_team_feed

    # conveyor-fed pick-and-place demo:
    python -m factorymind.sim.a.run_team_feed --scenario conveyor_feed

    # then serve for dashboard Live mode (second terminal):
    python -m factorymind.sim.a.serve_team_feed
"""

from __future__ import annotations

import argparse
import os
import shutil
import time

from pathlib import Path

from factorymind.sim.a.config import SimConfig
from factorymind.sim.a.env_factory import create_cell_env
from factorymind.sim.a.frame_export import latest_frame_path, replay_frame_url
from factorymind.sim.a.oracle import oracle_plan
from factorymind.sim.a.telemetry_bridge import (
    AR_PROFILE,
    DIFFUSION_PROFILE,
    append_rows,
    ar_run_path,
    c5_row_for_step,
    default_telemetry_path,
    diffusion_run_path,
    telemetry_dir,
    write_rows,
)


def _export_demo_samples() -> None:
    """Copy isolated runs beside the static dashboard for offline replay."""
    demo_static = Path(__file__).resolve().parents[2] / "demo" / "static"
    demo_static.mkdir(parents=True, exist_ok=True)
    for name in ("diffusion_run.jsonl", "ar_run.jsonl"):
        src = telemetry_dir() / name
        if src.is_file():
            shutil.copy2(src, demo_static / name)
            print(f"Demo copy: {demo_static / name}")


def run_feed(
    *,
    scenario: str = "default",
    seed: int = 0,
    max_steps: int = 50,
    stream: bool = False,
    interval: float = 1.0,
    export_demo: bool = True,
) -> dict:
    os.environ["FACTORYMIND_SIM_BACKEND"] = "mujoco"
    os.environ["FACTORYMIND_SIM_AUTO_FRAME"] = "1"

    if max_steps == 50 and scenario == "conveyor_feed":
        max_steps = 160

    cfg = SimConfig(backend="mujoco", scenario=scenario, default_seed=seed)  # type: ignore[arg-type]
    env = create_cell_env(cfg)
    env.reset(seed)

    diffusion_path = diffusion_run_path()
    ar_path = ar_run_path()
    live_path = default_telemetry_path()
    replay_path = telemetry_dir() / "oracle_replay.jsonl"
    for p in (diffusion_path, ar_path, live_path, replay_path):
        p.unlink(missing_ok=True)

    diffusion_rows: list[dict] = []
    ar_rows: list[dict] = []
    step_idx = 0

    def _record(plan, state: dict) -> None:
        nonlocal step_idx
        step_idx += 1
        base_ts = time.time()
        frame_url = replay_frame_url(state["step"])
        try:
            env.save_frame(f"replay/step_{state['step']:04d}.png")
        except Exception as exc:
            print(f"Frame skip step {state['step']}: {exc}")
            # Keep frame_url so dashboard can sync when frames exist on GB10 / after manual render

        d_row = c5_row_for_step(
            profile=DIFFUSION_PROFILE,
            step=state["step"],
            plan=plan,
            events=state.get("events", []),
            done=state["done"],
            ts=base_ts,
            frame_url=frame_url,
        )
        a_row = c5_row_for_step(
            profile=AR_PROFILE,
            step=state["step"],
            plan=plan,
            events=state.get("events", []),
            done=state["done"],
            ts=base_ts + 0.001,
            frame_url=frame_url,
        )
        diffusion_rows.append(d_row)
        ar_rows.append(a_row)
        if stream:
            append_rows(live_path, [d_row])

    try:
        env.save_frame("replay/step_0000.png")
    except Exception as exc:
        print(f"Initial frame skip: {exc}")

    initial = env.get_state()
    print(f"scenario: {initial.get('scenario')}")
    print(f"task: {initial.get('task')}")
    print(f"parts: {[(p['id'], p['color']) for p in initial.get('parts', [])]}")

    if stream:
        print(f"Streaming telemetry -> {live_path} (Ctrl+C to stop early)")

    for _ in range(max_steps):
        state = env.get_state()
        if state["done"]:
            break
        plan = oracle_plan(state)
        env.step(plan)
        state = env.get_state()
        _record(plan, state)
        if stream:
            time.sleep(interval)

    final = env.get_state()
    if not stream:
        write_rows(diffusion_path, diffusion_rows)
        write_rows(ar_path, ar_rows)
        write_rows(live_path, diffusion_rows)
        write_rows(replay_path, diffusion_rows)

    target_parts = [p for p in final.get("parts", []) if p.get("color") == "green"] if scenario == "sort_green" else final.get("parts", [])
    if scenario == "sort_green":
        placed = sum(1 for p in target_parts if p["at"] == "station_1")
        print(f"Done — step={final['step']}, green placed={placed}/{len(target_parts)}")
    else:
        placed = sum(1 for p in final.get("parts", []) if p["at"] == "station_1")
        print(f"Done — step={final['step']}, placed={placed}/{len(final.get('parts', []))}")

    print(f"Diffusion run: {diffusion_path} ({len(diffusion_rows)} rows)")
    print(f"AR run:        {ar_path} ({len(ar_rows)} rows)")
    print(f"Live alias:    {live_path}")
    print(f"Replay copy:   {replay_path}")
    print(f"Latest frame:  {latest_frame_path()}")
    n_frames = len(list(env._frames_dir.glob("replay/*.png")))  # type: ignore[attr-defined]
    print(f"Replay frames: {n_frames}")
    if export_demo and not stream:
        _export_demo_samples()
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="Oracle sim feed for B/C integration")
    parser.add_argument(
        "--scenario",
        default="default",
        choices=["default", "sort_green", "misaligned", "empty_bin", "conveyor_feed"],
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--stream", action="store_true", help="Append telemetry live (~1 Hz)")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--no-export-demo", action="store_true", help="Skip copy to demo/static/")
    args = parser.parse_args()
    run_feed(
        scenario=args.scenario,
        seed=args.seed,
        max_steps=args.max_steps,
        stream=args.stream,
        interval=args.interval,
        export_demo=not args.no_export_demo,
    )


if __name__ == "__main__":
    main()
