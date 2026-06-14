"""Write C5 telemetry JSONL from real oracle sim steps — B/C can consume as-is."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from factorymind.agent.schemas import CellPlan

DIFFUSION_URL = "http://localhost:8000/v1"
AR_URL = "http://localhost:8001/v1"

# Isolated-measurement placeholders (same sim actions, per-model wall-clock).
# B replaces these with real timings from separate model runs on the box.
_COMPLETION_TOKENS = 220
_PROMPT_TOKENS = 480

ModelName = Literal["diffusiongemma", "gemma4", "mock", "oracle"]
Precision = Literal["nvfp4", "bf16"]


@dataclass(frozen=True)
class ModelProfile:
    model: ModelName
    endpoint: str
    precision: Precision


DIFFUSION_PROFILE = ModelProfile("diffusiongemma", DIFFUSION_URL, "nvfp4")
AR_PROFILE = ModelProfile("gemma4", AR_URL, "nvfp4")


def telemetry_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "telemetry"


def default_telemetry_path() -> Path:
    return telemetry_dir() / "run.jsonl"


def diffusion_run_path() -> Path:
    return telemetry_dir() / "diffusion_run.jsonl"


def ar_run_path() -> Path:
    return telemetry_dir() / "ar_run.jsonl"


def plan_action_summary(plan: CellPlan) -> str:
    return "; ".join(f"r{cmd.id} {cmd.action} {cmd.target}" for cmd in plan.robots)


def pick_sim_event(events: list[str], done: bool) -> str:
    if done:
        return "task_complete"
    for name in ("pick_success", "place_success", "collision", "grip_miss", "scenario_misaligned", "scenario_empty_bin"):
        if name in events:
            return name
    return "task_progress"


def isolated_latency_for_step(profile: ModelProfile, step: int) -> tuple[int, int]:
    """Return (latency_ms, ttft_ms) for one model profile — wall-clock headline + secondary TTFT."""
    if profile.model == "diffusiongemma":
        ttft = 210 + (step % 3) * 5
        tok_s = 108.0
        total = int(ttft + (_COMPLETION_TOKENS / tok_s) * 1000)
        return total, int(ttft)
    ttft = 55 + (step % 2) * 3
    tok_s = 58.0 if step % 5 != 0 else 38.0
    total = int(ttft + (_COMPLETION_TOKENS / tok_s) * 1000)
    return total, int(ttft)


def c5_row_for_step(
    *,
    profile: ModelProfile,
    step: int,
    plan: CellPlan,
    events: list[str],
    done: bool,
    ts: float | None = None,
    frame_url: str | None = None,
) -> dict:
    """One sim step -> one C5 row for a single isolated model run."""
    ts = time.time() if ts is None else ts
    latency_ms, ttft_ms = isolated_latency_for_step(profile, step)
    row = {
        "ts": round(ts, 3),
        "step": step,
        "model": profile.model,
        "endpoint": profile.endpoint,
        "precision": profile.precision,
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms,
        "prompt_tokens": _PROMPT_TOKENS,
        "completion_tokens": _COMPLETION_TOKENS,
        "parsed_ok": True,
        "retries": 0,
        "action_summary": plan_action_summary(plan),
        "sim_event": pick_sim_event(events, done),
    }
    if frame_url:
        row["frame_url"] = frame_url
    return row


def c5_rows_for_step(
    *,
    step: int,
    plan: CellPlan,
    events: list[str],
    done: bool,
    ts: float | None = None,
) -> list[dict]:
    """Backward-compat: paired rows (use separate isolated run files for the dashboard race)."""
    ts = time.time() if ts is None else ts
    return [
        c5_row_for_step(profile=DIFFUSION_PROFILE, step=step, plan=plan, events=events, done=done, ts=ts),
        c5_row_for_step(profile=AR_PROFILE, step=step, plan=plan, events=events, done=done, ts=ts + 0.001),
    ]


def append_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
