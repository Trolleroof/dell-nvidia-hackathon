"""MCP server for the cell sim (stdio / HTTP).

Run (stdio — for Cursor / Claude Desktop):
    python -m factorymind.sim.a.mcp_server

Run (HTTP — for NemoClaw / OpenClaw remote clients):
    python -m factorymind.sim.a.mcp_server --http --port 8765
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from factorymind.agent.schemas import CellPlan
from dataclasses import replace
from factorymind.sim.a.config import get_config
from factorymind.sim.a.env_factory import get_cell_env, reset_cell_env
from factorymind.sim.a.frame_export import latest_frame_path, read_latest_frame_meta
from factorymind.sim.a.part_catalog import TASK_BY_SCENARIO
from factorymind.sim.a.targets import TARGET_POSES
from factorymind.sim.a.telemetry_bridge import (
    DIFFUSION_PROFILE,
    append_rows,
    c5_row_for_step,
    default_telemetry_path,
    telemetry_dir,
)

Scenario = Literal["default", "sort_green", "misaligned", "empty_bin", "conveyor_feed"]

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

# Live-feed bridge — when NemoClaw drives the sim through these tools, emit the
# same C5 telemetry + frames that the Role C dashboard polls on :8766. This is
# the merge point: NemoClaw's tool calls become the dashboard's live feed.
_last_step_ts: float | None = None


def _emit_live_telemetry(state: dict[str, Any], plan: CellPlan) -> None:
    """Append one C5 row to telemetry/run.jsonl for a NemoClaw-driven sim step.

    The headline `latency_ms` is the real wall-clock between successive tool
    calls — i.e. NemoClaw's decision cadence (model think-time + sim step).
    Falls back silently so a telemetry hiccup never blocks the control loop.
    """
    global _last_step_ts
    try:
        now = time.time()
        measured_ms = int((now - _last_step_ts) * 1000) if _last_step_ts else None
        _last_step_ts = now

        step = state.get("step", 0)
        row = c5_row_for_step(
            profile=DIFFUSION_PROFILE,
            step=step,
            plan=plan,
            events=state.get("events", []),
            done=state.get("done", False),
            ts=now,
            frame_url="/sim/latest.png",
        )
        # Override the synthetic latency with the real measured cadence when known.
        if measured_ms is not None:
            row["latency_ms"] = measured_ms
        append_rows(default_telemetry_path(), [row])
    except Exception:
        pass


def _save_live_frame(label: str = "") -> None:
    """Render the current sim to frames/latest.png for the dashboard poll."""
    try:
        env = get_cell_env()
        if hasattr(env, "save_frame"):
            env.save_frame()
    except Exception:
        pass


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
    # Push into the env so the oracle's part filter and done-check honour it
    # (e.g. "pick the yellow only" stops after the yellow cube).
    try:
        env = get_cell_env()
        if hasattr(env, "set_task"):
            env.set_task(_current_task)
    except Exception:
        pass
    return {"status": "ok", "task": _current_task}


@mcp.tool()
def get_task() -> dict[str, str]:
    """Return the current task instruction (UI Prompt)."""
    return {"task": _current_task}


# ── Sim state tools ───────────────────────────────────────────────────────────

@mcp.tool()
def reset_cell(seed: int = 0, scenario: Scenario = "default") -> dict[str, Any]:
    """Reset the cell. scenario: default | sort_green | misaligned | empty_bin | conveyor_feed.

    Args:
        seed: Random seed for deterministic physics.
        scenario: Initial layout / task preset.
    """
    global _current_task, _last_step_ts
    cfg = replace(get_config(), scenario=scenario, default_seed=seed)
    cell = reset_cell_env(cfg)
    _current_task = TASK_BY_SCENARIO.get(scenario, _current_task)
    result = cell.reset(seed)
    # Start a fresh live feed: truncate telemetry (keep the file so the dashboard
    # live poll gets 200/empty rather than 404), reset cadence clock, publish frame 0.
    try:
        path = default_telemetry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    except Exception:
        pass
    _last_step_ts = None
    _save_live_frame("reset")
    return result


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

    # Merge point: publish frame + telemetry so the Role C dashboard's live
    # feed (:8766) reflects this NemoClaw-driven step in real time.
    _save_live_frame("step")
    _emit_live_telemetry(result, plan)

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
def list_targets() -> dict[str, list[str]]:
    """List valid named targets for move/grip/release commands."""
    return {"targets": get_cell_env().list_targets()}


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
                    "events": ["pick_success", "collision", "task_complete", "scenario_misaligned", "scenario_conveyor_feed"],
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


_DIFFUSIONGEMMA_BASE_URL = "http://localhost:8000/v1"
_DIFFUSIONGEMMA_MODEL = "diffusiongemma"
_VALID_COLORS = {"yellow", "blue", "green", "all"}
_VALID_STATIONS = {"station_1", "station_2"}


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Parse the first JSON object from model text, tolerating prefixes."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    value = json.loads(text[start : idx + 1])
                except Exception:
                    return None
                return value if isinstance(value, dict) else None
    return None


def _fallback_intent_from_prompt(instruction: str) -> dict[str, str]:
    lower = instruction.lower().replace("-", "_")
    station = "station_2" if re.search(r"station[_ ]?2", lower) else "station_1"
    color = "all"
    for candidate in ("green", "blue", "yellow"):
        if candidate in lower:
            color = candidate
            break
    return {"color": color, "target_station": station}


def _normalize_intent(raw: dict[str, Any] | None, instruction: str) -> dict[str, str]:
    fallback = _fallback_intent_from_prompt(instruction)
    if not raw:
        return fallback
    color = str(raw.get("color") or raw.get("part_color") or fallback["color"]).lower().strip()
    station = str(raw.get("target_station") or raw.get("station") or fallback["target_station"]).lower().strip()
    station = station.replace(" ", "_").replace("-", "_")
    if station in {"station2", "2"}:
        station = "station_2"
    elif station in {"station1", "1"}:
        station = "station_1"
    if color not in _VALID_COLORS:
        color = fallback["color"]
    if station not in _VALID_STATIONS:
        station = fallback["target_station"]
    return {"color": color, "target_station": station}


def _canonical_task_from_intent(intent: dict[str, str]) -> str:
    color = intent["color"]
    station = intent["target_station"]
    if color == "all":
        return f"Pick all parts from bin_a and place them on {station}."
    return f"Sort the {color} parts into {station}."


def _diffusiongemma_intent(instruction: str, state: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    """Use DiffusionGemma only for prompt intent; deterministic code executes."""
    fallback = _fallback_intent_from_prompt(instruction)
    available = [
        {"id": p.get("id"), "color": p.get("color"), "at": p.get("at")}
        for p in state.get("parts", [])
    ]
    prompt = (
        "JSON only. Extract a factory sorting intent. "
        "Return exactly one object like "
        "{\"color\":\"green\",\"target_station\":\"station_2\"}. "
        "Allowed color values: green, blue, yellow, all. "
        "Allowed target_station values: station_1, station_2. "
        f"Available parts: {json.dumps(available, separators=(',', ':'))}. "
        f"Command: {instruction}"
    )
    body = json.dumps(
        {
            "model": _DIFFUSIONGEMMA_MODEL,
            "messages": [
                {"role": "system", "content": "You output only one valid JSON object and no prose."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 32,
            "stream": False,
        }
    ).encode()
    meta: dict[str, Any] = {"source": "diffusiongemma", "fallback_used": False}
    try:
        req = urllib.request.Request(
            f"{_DIFFUSIONGEMMA_BASE_URL}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=2) as resp:
            payload = json.loads(resp.read())
        meta["latency_ms"] = int((time.monotonic() - t0) * 1000)
        usage = payload.get("usage") or {}
        if usage:
            meta["usage"] = usage
        content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        meta["raw"] = str(content)[:500]
        parsed = _extract_json_object(str(content))
        if parsed is None:
            meta.update({"fallback_used": True, "error": "diffusiongemma returned no parseable JSON"})
            return fallback, meta
        return _normalize_intent(parsed, instruction), meta
    except Exception as exc:
        meta.update({"source": "keyword_fallback", "fallback_used": True, "error": str(exc)})
        return fallback, meta


# ── Browser bridge — frontend "Queue command" → real sim action ────────────────
# The Role C dashboard runs in a browser and cannot do the MCP session handshake
# cleanly, so we expose a plain CORS-enabled REST endpoint in the SAME process
# (which owns the sim env singleton). Posting an instruction sets the task and
# drives the deterministic oracle policy — the plan's guaranteed safety net — so
# the operator sees the cell move and the live feed update immediately. When
# NemoClaw runs its own loop it drives the same env via the MCP tools above.

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _safe_file_under(root: Path, rel: str) -> Path | None:
    """Resolve rel under root; reject path traversal."""
    from pathlib import Path as _Path

    base = _Path(root).resolve()
    try:
        target = (base / rel).resolve()
        target.relative_to(base)
    except ValueError:
        return None
    return target if target.is_file() else None


@mcp.custom_route("/scenario", methods=["POST", "OPTIONS"])
@mcp.custom_route("/reset", methods=["POST", "OPTIONS"])
async def reset_route(request):  # type: ignore[no-untyped-def]
    from starlette.responses import JSONResponse

    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_CORS_HEADERS)

    try:
        body = await request.json()
    except Exception:
        body = {}

    seed = int(body.get("seed", 0))
    scenario = str(body.get("scenario", "default")).strip() or "default"
    if scenario not in {"default", "sort_green", "misaligned", "empty_bin", "conveyor_feed"}:
        scenario = "default"

    state = reset_cell(seed=seed, scenario=scenario)  # type: ignore[arg-type]
    return JSONResponse({"ok": True, **state}, headers=_CORS_HEADERS)


@mcp.custom_route("/command", methods=["POST", "OPTIONS"])
async def queue_command(request):  # type: ignore[no-untyped-def]
    from starlette.responses import JSONResponse

    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_CORS_HEADERS)

    global _current_task, _last_step_ts
    try:
        body = await request.json()
    except Exception:
        body = {}
    instruction = str(body.get("instruction", "")).strip()
    steps = int(body.get("steps", 5))
    steps = max(1, min(steps, 50))

    from factorymind.sim.a.oracle import oracle_plan

    env = get_cell_env()
    executed: list[dict[str, Any]] = []
    state = env.get_state()

    # A new operator command should always produce a visible run. If the previous
    # episode already finished, start a fresh one so steps > 0.
    did_reset = False
    if state.get("done"):
        env.reset(0)
        try:
            default_telemetry_path().write_text("")
        except Exception:
            pass
        _last_step_ts = None
        _save_live_frame("command-reset")
        state = env.get_state()
        did_reset = True

    intent: dict[str, str] | None = None
    intent_meta: dict[str, Any] = {"source": "none", "fallback_used": False}
    if instruction:
        intent, intent_meta = _diffusiongemma_intent(instruction, state)
        _current_task = _canonical_task_from_intent(intent)

    # Apply the operator's prompt AFTER any reset so it isn't clobbered by the
    # scenario default. DiffusionGemma handles intent extraction; the deterministic
    # controller handles safe, fast execution of that intent.
    if hasattr(env, "set_task"):
        env.set_task(_current_task)
        state = env.get_state()

    for _ in range(steps):
        if state.get("done"):
            break
        plan = oracle_plan(state)
        state = env.step(plan)
        _save_live_frame("command")
        _emit_live_telemetry(state, plan)
        executed.append(
            {
                "step": state.get("step"),
                "action": "; ".join(
                    f"r{c.id} {c.action} {c.target}" for c in plan.robots
                ),
                "events": state.get("events", []),
            }
        )

    return JSONResponse(
        {
            "ok": True,
            "task": _current_task,
            "operator_prompt": instruction,
            "intent": intent,
            "intent_meta": intent_meta,
            "steps_run": len(executed),
            "did_reset": did_reset,
            "done": state.get("done", False),
            "executed": executed,
            "feed": "http://localhost:8765/telemetry/run.jsonl",
        },
        headers=_CORS_HEADERS,
    )


@mcp.custom_route("/sim/{filepath:path}", methods=["GET", "OPTIONS"])
async def sim_frame_route(request):  # type: ignore[no-untyped-def]
    """Serve MuJoCo PNG frames — same contract as serve_team_feed on :8766."""
    from pathlib import Path

    from starlette.responses import FileResponse, JSONResponse, Response

    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_CORS_HEADERS)

    filepath = str(request.path_params.get("filepath", "")).lstrip("/")
    if not filepath:
        return Response(status_code=404)

    frames_root = Path(latest_frame_path().parent)
    target = _safe_file_under(frames_root, filepath)
    if target is None:
        return Response(status_code=404)

    return FileResponse(
        target,
        media_type="image/png",
        headers={**_CORS_HEADERS, "Cache-Control": "no-store"},
    )


@mcp.custom_route("/telemetry/{filepath:path}", methods=["GET", "OPTIONS"])
async def telemetry_file_route(request):  # type: ignore[no-untyped-def]
    """Serve live JSONL telemetry for the dashboard poll loop."""
    from starlette.responses import FileResponse, JSONResponse, Response

    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_CORS_HEADERS)

    filepath = str(request.path_params.get("filepath", "")).lstrip("/")
    if not filepath or "/" in filepath or filepath.startswith("."):
        return Response(status_code=404)

    target = _safe_file_under(telemetry_dir(), filepath)
    if target is None:
        return Response(status_code=404)

    return FileResponse(
        target,
        media_type="application/x-ndjson",
        headers={**_CORS_HEADERS, "Cache-Control": "no-store"},
    )


@mcp.custom_route("/sim/state", methods=["GET", "OPTIONS"])
async def sim_state_route(request):  # type: ignore[no-untyped-def]
    from starlette.responses import JSONResponse

    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_CORS_HEADERS)

    env = get_cell_env()
    state = env.get_state()
    return JSONResponse(state, headers=_CORS_HEADERS)


@mcp.custom_route("/step_plan", methods=["POST", "OPTIONS"])
async def step_plan_route(request):  # type: ignore[no-untyped-def]
    """Execute one sim step using a CellPlan supplied by an LLM (not the oracle).

    Body: { "plan_json": "<CellPlan JSON string>" }
    Returns the new sim state + events.
    """
    from starlette.responses import JSONResponse

    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_CORS_HEADERS)

    try:
        body = await request.json()
    except Exception:
        body = {}

    plan_json = body.get("plan_json", "")
    if not plan_json:
        return JSONResponse({"ok": False, "error": "plan_json required"}, status_code=400, headers=_CORS_HEADERS)

    try:
        import json as _json
        raw = _json.loads(plan_json)
        plan = CellPlan.model_validate(raw)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"invalid plan_json: {e}"}, status_code=400, headers=_CORS_HEADERS)

    result = get_cell_env().step(plan)
    _save_live_frame("step_plan")
    _emit_live_telemetry(result, plan)

    return JSONResponse({"ok": True, **result}, headers=_CORS_HEADERS)


@mcp.custom_route("/teleport_part", methods=["POST", "OPTIONS"])
async def teleport_part_route(request):  # type: ignore[no-untyped-def]
    from starlette.responses import JSONResponse

    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_CORS_HEADERS)

    try:
        body = await request.json()
    except Exception:
        body = {}

    part_id = str(body.get("part_id", "")).strip()
    target = str(body.get("target", "")).strip()

    if not part_id or not target:
        return JSONResponse({"ok": False, "error": "part_id and target required"}, headers=_CORS_HEADERS)

    env = get_cell_env()
    if not hasattr(env, "teleport_part"):
        return JSONResponse(
            {"ok": False, "error": "teleport_part not supported on mock backend"},
            headers=_CORS_HEADERS,
        )

    result = env.teleport_part(part_id, target)  # type: ignore[attr-defined]
    if result.get("ok"):
        _save_live_frame("teleport")
    return JSONResponse(result, headers=_CORS_HEADERS)


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
