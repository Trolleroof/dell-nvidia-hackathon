"""Generate mock C5 telemetry JSONL for the Role C dashboard.

This is a standalone, GPU-free stand-in for Role B's telemetry writer. It emits
the frozen C5 schema (one line per model per control step) so the dashboard's
Replay / Live modes can be rehearsed before the box exists.

Usage:
    # write a recorded file for Replay mode (load it from the dashboard):
    python -m factorymind.demo.gen_mock_telemetry --steps 80 --out static/sample_telemetry.jsonl

    # stream forever into the shared telemetry dir for Live mode:
    python -m factorymind.demo.gen_mock_telemetry --stream --out ../../telemetry/run.jsonl

C5 schema (per line):
    ts, step, model, endpoint, latency_ms, ttft_ms, prompt_tokens,
    completion_tokens, parsed_ok, retries, action_summary, sim_event
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time

DIFFUSION_URL = "http://localhost:8000/v1"
AR_URL = "http://localhost:8001/v1"

TARGETS = ["bin_a", "bin_b", "station_1", "station_2", "part_1", "part_2", "part_3"]
ACTIONS = ["move", "grip", "release", "hold"]
EVENTS = ["pick_success", "place_success", "task_progress", "handoff", "collision"]


def _action_summary() -> str:
    return (
        f"r0 {random.choice(ACTIONS)} {random.choice(TARGETS)}; "
        f"r1 {random.choice(ACTIONS)} {random.choice(TARGETS)}"
    )


def decision_pair(step: int, ts: float) -> list[dict]:
    """One control decision -> a diffusion row and an AR row over identical work.

    Honest framing: diffusion has HIGHER time-to-first-token but HIGHER tok/s on
    long outputs; AR has low TTFT but lower throughput and occasional stutter.
    """
    completion = random.randint(200, 260)  # identical max-tokens => fair race
    prompt = random.randint(420, 520)
    summary = _action_summary()
    event = random.choice(EVENTS)

    # --- DiffusionGemma (hero, parallel) ---
    d_tok_s = random.uniform(98, 124)
    d_ttft = random.uniform(190, 250)
    d_parsed, d_retries = True, 0
    if random.random() < 0.06:  # diffusion can emit layout artifacts -> retry once
        d_parsed, d_retries, d_tok_s = False, 1, d_tok_s * 0.82
    d_total = d_ttft + (completion / d_tok_s) * 1000

    # --- Gemma 4 (AR baseline, sequential) ---
    a_tok_s = random.uniform(52, 66)
    a_ttft = random.uniform(45, 80)
    if random.random() < 0.10:  # stutter: throughput dips
        a_tok_s *= random.uniform(0.45, 0.7)
    a_total = a_ttft + (completion / a_tok_s) * 1000

    return [
        {
            "ts": round(ts, 3),
            "step": step,
            "model": "diffusiongemma",
            "endpoint": DIFFUSION_URL,
            "latency_ms": round(d_total),
            "ttft_ms": round(d_ttft),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "parsed_ok": d_parsed,
            "retries": d_retries,
            "action_summary": summary,
            "sim_event": event,
        },
        {
            "ts": round(ts + 0.001, 3),
            "step": step,
            "model": "gemma4",
            "endpoint": AR_URL,
            "latency_ms": round(a_total),
            "ttft_ms": round(a_ttft),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "parsed_ok": True,
            "retries": 0,
            "action_summary": summary,
            "sim_event": event,
        },
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate mock C5 telemetry JSONL.")
    ap.add_argument("--steps", type=int, default=80, help="number of control decisions")
    ap.add_argument("--out", default="static/sample_telemetry.jsonl", help="output JSONL path")
    ap.add_argument("--stream", action="store_true", help="append forever (~1 decision/sec) for Live mode")
    ap.add_argument("--seed", type=int, default=7, help="RNG seed for reproducible recordings")
    ap.add_argument("--interval", type=float, default=1.0, help="seconds between decisions in --stream mode")
    args = ap.parse_args(argv)

    random.seed(args.seed)

    if args.stream:
        step = 0
        # truncate the live file so the dashboard starts clean
        open(args.out, "w").close()
        print(f"[gen] streaming mock telemetry -> {args.out} (Ctrl+C to stop)", file=sys.stderr)
        try:
            while True:
                step += 1
                with open(args.out, "a", encoding="utf-8") as f:
                    for row in decision_pair(step, time.time()):
                        f.write(json.dumps(row) + "\n")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\n[gen] stopped at step {step}", file=sys.stderr)
            return 0

    with open(args.out, "w", encoding="utf-8") as f:
        t = time.time()
        for step in range(1, args.steps + 1):
            for row in decision_pair(step, t):
                f.write(json.dumps(row) + "\n")
            t += 1.0
    print(f"[gen] wrote {args.steps} decisions ({args.steps * 2} rows) -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
