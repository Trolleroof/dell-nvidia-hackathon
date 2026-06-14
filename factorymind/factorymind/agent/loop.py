"""Standalone Python control loop — NO-MCP fallback / smoke-test path.

Drives MockCellEnv directly (no MCP server, no OpenClaw runtime).
Use this to verify the sim + LLM planner end-to-end without any agent framework.

Primary path (OpenClaw + MCP) lives in agent/skills/ + agent/openclaw.json.

Run directly:
    python -m factorymind.agent.loop --mode mock
    python -m factorymind.agent.loop --mode local --model diffusiongemma-18b
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field

from factorymind.agent.client import LLMClient, PlanResult, make_client
from factorymind.sim.mock_cell import MockCellEnv


@dataclass
class LoopStats:
    steps: int = 0
    total_latency_ms: float = 0.0
    retries: int = 0
    model: str = ""
    wall_seconds: float = 0.0
    log: list[dict] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.steps if self.steps else 0.0


def run_loop(
    client: LLMClient,
    env: MockCellEnv,
    max_steps: int = 100,
    verbose: bool = False,
    seed: int = 0,
) -> LoopStats:
    """Run the read → plan → step loop until done or max_steps."""
    env.reset(seed)
    stats = LoopStats()
    t_start = time.monotonic()

    for _ in range(max_steps):
        state = env.get_state()
        if state["done"]:
            break

        result: PlanResult = client.plan(state)
        stats.model = result.model
        stats.steps += 1
        stats.total_latency_ms += result.latency_ms
        stats.retries += result.retries

        entry = {
            "step": stats.steps,
            "model": result.model,
            "latency_ms": round(result.latency_ms, 1),
            "retries": result.retries,
            "plan": result.plan.plan,
        }
        stats.log.append(entry)

        if verbose:
            print(json.dumps(entry))

        new_state = env.step(result.plan)

        events = new_state.get("events", [])
        for evt in events:
            if evt in ("pick_success", "place_success", "task_complete"):
                print(f"  [{stats.steps}] {evt}")
            elif evt not in ("",):
                print(f"  [{stats.steps}] ERROR: {evt} — replanning")

    stats.wall_seconds = time.monotonic() - t_start
    return stats


def print_report(stats: LoopStats) -> None:
    print(
        f"\nDone in {stats.steps} steps ({stats.wall_seconds:.1f}s). "
        f"Avg plan latency: {stats.avg_latency_ms:.0f}ms "
        f"[{stats.model}]. Retries: {stats.retries}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="FactoryMind control loop")
    parser.add_argument("--mode", choices=["mock", "local"], default="mock")
    parser.add_argument("--model", default="diffusiongemma-18b")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    client = make_client(mode=args.mode, base_url=args.base_url, model=args.model)
    env = MockCellEnv(num_robots=2, seed=args.seed)

    print(f"Running loop: mode={args.mode}, model={args.model}, max_steps={args.max_steps}")
    stats = run_loop(client, env, max_steps=args.max_steps, verbose=args.verbose, seed=args.seed)
    print_report(stats)


if __name__ == "__main__":
    main()
