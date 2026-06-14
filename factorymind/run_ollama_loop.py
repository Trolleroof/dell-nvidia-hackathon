"""
Drive the FactoryMind MCP server with Ollama as the LLM.
Proves the full LLM → MCP → sim pipeline end-to-end.

Each step:
  1. GET /sim/state  — read current sim state
  2. POST Ollama     — generate a CellPlan JSON
  3. POST /step_plan — execute that exact plan in the sim

Usage:
    python run_ollama_loop.py [--steps 20] [--model llama3.2:3b]
"""
import argparse
import json
import time
import urllib.request

MCP_BASE = "http://localhost:8765"
OLLAMA_BASE = "http://localhost:11434/v1"

SYSTEM_PROMPT = """\
You are FactoryMind, a factory floor robot controller.
Output ONLY a raw JSON object — no markdown, no code fences, no explanation.

The JSON must have exactly this structure:
{
  "plan": "one sentence describing what you are doing",
  "robots": [
    {"id": 0, "action": "move", "target": "bin_a", "reason": "go to pick up part"},
    {"id": 1, "action": "hold", "target": "home", "reason": "wait"}
  ]
}

Rules:
- "action" must be exactly one of: move, grip, release, hold
- "target" must be exactly one of: bin_a, bin_b, station_1, station_2, part_1, part_2, part_3, home
- Always include both robot id 0 and robot id 1
- Pick-and-place sequence: move to location → grip part → move to destination → release

Pick-and-place workflow to move a part:
  Step 1: robot action=move, target=bin_a (approach the bin)
  Step 2: robot action=grip, target=part_1 (or part_2, part_3)
  Step 3: robot action=move, target=station_1 (carry to station)
  Step 4: robot action=release, target=station_1 (drop at station)
"""


def http_post(url: str, body: dict) -> dict:
    import urllib.error
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {detail}") from None


def http_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def get_state() -> dict:
    return http_get(f"{MCP_BASE}/sim/state")


def reset_sim() -> None:
    http_post(f"{MCP_BASE}/command", {
        "instruction": "Pick all parts from bin_a and place them on station_1.",
        "steps": 0,
    })


def _extract_json(text: str) -> dict:
    """Extract first complete JSON object from LLM output, tolerant of trailing prose."""
    if "```" in text:
        for part in text.split("```"):
            part = part.strip().lstrip("json").strip()
            try:
                return json.loads(part)
            except Exception:
                pass
    # Walk brace depth to find the first complete {...} block
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found in LLM output")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unterminated JSON object in LLM output")


def ollama_plan(state: dict, model: str) -> tuple[dict, float]:
    # Send only essential fields to keep prompt small
    compact = {
        "step": state.get("step"),
        "task": state.get("task"),
        "robots": state.get("robots"),
        "parts": [{"id": p["id"], "at": p["at"]} for p in state.get("parts", [])],
        "stations": state.get("stations"),
    }
    user_msg = f"Cell state:\n{json.dumps(compact)}\n\nNext CellPlan:"
    t0 = time.monotonic()
    resp = http_post(f"{OLLAMA_BASE}/chat/completions", {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.0,
        "stream": False,
    })
    latency_ms = (time.monotonic() - t0) * 1000
    raw = resp["choices"][0]["message"]["content"]
    return _extract_json(raw), latency_ms


def step_with_plan(plan: dict) -> dict:
    return http_post(f"{MCP_BASE}/step_plan", {"plan_json": json.dumps(plan)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--model", default="llama3.2:3b")
    args = parser.parse_args()

    print(f"\nFactoryMind — Ollama LLM Loop")
    print(f"  model:    {args.model}")
    print(f"  MCP:      {MCP_BASE}")
    print(f"  Ollama:   {OLLAMA_BASE}")
    print(f"  max steps: {args.steps}\n")

    reset_sim()
    state = get_state()
    print(f"Task:  {state.get('task', 'unknown')}")
    print(f"Parts: {[p['id'] + '@' + p['at'] for p in state.get('parts', [])]}\n")

    total_latency = 0.0
    completed = 0

    for i in range(args.steps):
        state = get_state()
        if state.get("done"):
            print(f"\n✓ Task complete at step {state.get('step')}!")
            break

        print(f"[{i+1:02d}] Asking {args.model}...", end=" ", flush=True)
        try:
            plan, latency_ms = ollama_plan(state, args.model)
            total_latency += latency_ms
            completed += 1
            intent = plan.get("plan", "")[:55]
            print(f"{latency_ms:.0f}ms  \"{intent}\"")
        except Exception as e:
            print(f"LLM error ({e}) — skipping step")
            continue

        try:
            result = step_with_plan(plan)
            events = result.get("events", [])
            if events:
                tag = "✓" if any(e in events for e in ("pick_success", "place_success", "task_complete")) else "!"
                print(f"     {tag} {', '.join(events)}")
            if result.get("done"):
                print(f"\n✓ Task complete at step {result.get('step')}!")
                break
        except RuntimeError as e:
            err = str(e)
            if "validation" in err or "literal_error" in err:
                print(f"     invalid plan (schema error) — skipping step")
            else:
                print(f"     sim error: {err[:120]}")

    state = get_state()
    avg = total_latency / max(completed, 1)
    parts = [f"{p['id']}@{p['at']}" for p in state.get("parts", [])]
    print(f"\nFinal state: step={state.get('step')}, done={state.get('done')}")
    print(f"Parts:       {parts}")
    print(f"Avg LLM latency: {avg:.0f}ms [{args.model}]")
    print(f"\nWatch live at: http://localhost:8766/  or  http://localhost:5173/")


if __name__ == "__main__":
    main()
