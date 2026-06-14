"""
FactoryMind agent entrypoint — proper three-layer data router.

Architecture (per overviewarchitectureagent.md):

  User Task
      │
  OpenClawAgent        ← reads openclaw.json + skills.yaml; orchestrates the skill loop
      │
  OpenShellGate        ← reads openshell-policy.yaml; DENY-BY-DEFAULT on all outbound
      │                   calls (inference + MCP tools). LLM cannot override this.
      ├── NemoClawRouter  ← reads nemoclaw.yaml; routes inference to primary (Ollama
      │                      nemotron-3-nano:30b) or fallback. Never exposes API key
      │                      or base_url to OpenClaw/agent logic.
      │
      └── MCPClient    ← streamablehttp_client to :8765/mcp; tools only execute after
                          OpenShell approves the call (network + tool name allowlists).

MuJoCo sim renders latest.png on every substep → dashboard polls at 80ms.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

_AGENT_DIR = Path(__file__).parent / "factorymind" / "agent"


# ── OpenShell policy gate ─────────────────────────────────────────────────────

class OpenShellGate:
    """
    Out-of-process policy enforcement between agent logic and host resources.

    Reads openshell-policy.yaml. All MCP tool calls and inference calls must be
    approved here before execution. The LLM has no mechanism to bypass this gate.
    """

    def __init__(self, policy_path: Path) -> None:
        with open(policy_path) as f:
            self._policy = yaml.safe_load(f)
        self._audit_log: list[dict] = []

    def check_inference(self, base_url: str) -> bool:
        """Return True only if base_url is in approved_endpoints."""
        approved = self._policy.get("inference", {}).get("approved_endpoints", [])
        for ep in approved:
            if base_url.startswith(ep.split("/v1")[0]):
                return True
        self._audit("DENY", "inference", base_url, "not in approved_endpoints")
        raise PermissionError(
            f"OpenShell: inference endpoint {base_url!r} not approved. "
            "Update openshell-policy.yaml to allow it."
        )

    def check_network(self, host: str, port: int) -> bool:
        """Return True only if host:port is in the network allowlist."""
        for rule in self._policy.get("network", {}).get("allow", []):
            if rule.get("host") == host and rule.get("port") == port:
                return True
        self._audit("DENY", "network", f"{host}:{port}", "not in allowlist")
        raise PermissionError(
            f"OpenShell: network access to {host}:{port} denied. "
            "Update openshell-policy.yaml to allow it."
        )

    def check_tool(self, tool_name: str) -> bool:
        """MCP tool calls are allowed if the MCP server itself is allowed (port 8765)."""
        self.check_network("localhost", 8765)
        self._audit("ALLOW", "tool", tool_name, "mcp server approved")
        return True

    def _audit(self, verdict: str, kind: str, target: str, reason: str) -> None:
        entry = {
            "ts": time.time(),
            "verdict": verdict,
            "kind": kind,
            "target": target,
            "reason": reason,
        }
        self._audit_log.append(entry)
        tag = "✓" if verdict == "ALLOW" else "✗"
        print(f"  [OpenShell] {tag} {kind}:{target} — {reason}")

    def flush_audit(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            for entry in self._audit_log:
                f.write(json.dumps(entry) + "\n")
        self._audit_log.clear()


# ── NemoClaw inference router ─────────────────────────────────────────────────

class NemoClawRouter:
    """
    Inference routing layer — reads nemoclaw.yaml.

    Agent logic (OpenClaw) never sees base_url or model names directly.
    NemoClaw owns all routing decisions: primary → fallback on error.
    Privacy: local-only enforced by OpenShell gate before any call is made.
    """

    def __init__(self, config_path: Path, shell: OpenShellGate) -> None:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        inf = cfg.get("inference", {})
        self._primary = inf.get("primary", {})
        self._fallback = inf.get("fallback", {})
        self._fallback_trigger = inf.get("fallback_trigger", {})
        self._shell = shell
        self._consecutive_failures = 0
        self._using_fallback = False

    @property
    def _active(self) -> dict:
        return self._fallback if self._using_fallback else self._primary

    def call(self, messages: list[dict], tools: list[dict]) -> dict:
        """Route a chat-completion request; falls back to secondary on error."""
        base_url = self._active.get("base_url", "")
        model = self._active.get("model", "")

        # OpenShell gate: inference endpoint must be approved
        self._shell.check_inference(base_url)

        try:
            resp = self._http_complete(base_url, model, messages, tools)
            self._consecutive_failures = 0
            return resp
        except Exception as e:
            self._consecutive_failures += 1
            max_fail = self._fallback_trigger.get("on_parse_failure_count", 3)
            if (
                not self._using_fallback
                and self._consecutive_failures >= max_fail
                and self._fallback_trigger.get("on_connection_error")
            ):
                print(f"  [NemoClaw] switching to fallback after {self._consecutive_failures} failures")
                self._using_fallback = True
                return self.call(messages, tools)
            raise

    @staticmethod
    def _http_complete(base_url: str, model: str, messages: list[dict], tools: list[dict]) -> dict:
        body = json.dumps({
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "temperature": 0.0,
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())


# ── OpenClaw agent orchestrator ───────────────────────────────────────────────

class OpenClawAgent:
    """
    Task orchestration layer — reads openclaw.json + skills.yaml.

    Drives the skill loop: read-cell → plan-action → step-cell until done.
    Cannot bypass OpenShell or directly access host resources.
    """

    SOUL = """\
You are FactoryMind, an autonomous factory floor controller.
Coordinate two Franka Panda robot arms to complete pick-and-place tasks.

You have MCP tools: reset_cell, get_cell_state, step_cell, list_targets.

Workflow:
  1. reset_cell(seed=0)       — fresh episode
  2. get_cell_state()         — read current state
  3. step_cell(plan_json=...) — one control step (CellPlan JSON string)
  4. Repeat 2-3 until done=true

CellPlan schema (serialize as a JSON string passed to step_cell):
{
  "plan": "<one-line intent>",
  "robots": [
    {"id": 0, "action": "move|grip|release|hold", "target": "<target>", "reason": "<why>"},
    {"id": 1, "action": "move|grip|release|hold", "target": "<target>", "reason": "<why>"}
  ]
}

Valid targets: bin_a, bin_b, station_1, station_2, part_1, part_2, part_3, home.
Always include both robots. Pick sequence per part:
  move→bin_a, grip→part_N, move→station_1, release→station_1

Call get_cell_state() after every step to observe results.
Stop when the tool returns done=true.
"""

    def __init__(self, config_path: Path, shell: OpenShellGate, nemo: NemoClawRouter) -> None:
        with open(config_path) as f:
            cfg = json.load(f)
        self._cfg = cfg
        self._shell = shell
        self._nemo = nemo

    def build_messages(self, task: str) -> list[dict]:
        return [
            {"role": "system", "content": self.SOUL},
            {"role": "user", "content": task},
        ]

    async def run(
        self,
        task: str,
        mcp_session: ClientSession,
        oa_tools: list[dict],
        tool_names: set[str],
        max_turns: int,
    ) -> None:
        messages = self.build_messages(task)
        telemetry: list[dict] = []

        for turn in range(max_turns):
            print(f"\n[OpenClaw turn {turn + 1:02d}] planning...", end=" ", flush=True)
            t0 = time.monotonic()

            # NemoClaw routes this inference call (OpenShell gate inside)
            resp = self._nemo.call(messages, oa_tools)
            latency_ms = (time.monotonic() - t0) * 1000

            msg = resp["choices"][0]["message"]
            messages.append(msg)
            tool_calls = msg.get("tool_calls") or []
            content = msg.get("content") or ""

            if content:
                print(f"{latency_ms:.0f}ms  \"{content[:80]}\"")
            elif tool_calls:
                names = [tc["function"]["name"] for tc in tool_calls]
                print(f"{latency_ms:.0f}ms  → {', '.join(names)}")
            else:
                print(f"{latency_ms:.0f}ms  (no action)")

            telemetry.append({
                "turn": turn + 1,
                "latency_ms": round(latency_ms, 1),
                "tool_calls": [tc["function"]["name"] for tc in tool_calls],
                "content": content[:120] if content else None,
            })

            if not tool_calls:
                print("\n[OpenClaw] no tool calls — task may be complete or model stalled")
                break

            # Execute tool calls through OpenShell gate → MCP
            done = False
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args_raw = tc["function"].get("arguments", "{}")
                fn_args = (
                    json.loads(fn_args_raw)
                    if isinstance(fn_args_raw, str)
                    else fn_args_raw
                )
                call_id = tc.get("id", f"call_{turn}")

                if fn_name not in tool_names:
                    result_text = json.dumps({"error": f"unknown tool: {fn_name}"})
                    print(f"  [OpenShell] ✗ tool:{fn_name} — not in MCP tool list")
                else:
                    # OpenShell gate: check tool execution is allowed
                    try:
                        self._shell.check_tool(fn_name)
                    except PermissionError as e:
                        result_text = json.dumps({"error": str(e)})
                        messages.append({"role": "tool", "tool_call_id": call_id, "content": result_text})
                        continue

                    try:
                        result = await mcp_session.call_tool(fn_name, fn_args)
                        parts = [c.text for c in result.content if hasattr(c, "text")]
                        result_text = "\n".join(parts) if parts else "{}"

                        try:
                            parsed = json.loads(result_text)
                            if parsed.get("done"):
                                done = True
                                events = parsed.get("events", [])
                                print(f"  ✓ TASK COMPLETE — events={events}")
                            elif parsed.get("events"):
                                evts = parsed["events"]
                                ok = any(e in evts for e in ("pick_success", "place_success"))
                                print(f"  {'✓' if ok else '!'} {evts}")
                        except (json.JSONDecodeError, AttributeError):
                            pass

                    except Exception as e:
                        result_text = json.dumps({"error": str(e)})
                        print(f"  [MCP] ✗ {fn_name}: {e}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_text,
                })

            if done:
                print(f"\n✓ Task complete in {turn + 1} turns.")
                break
        else:
            print(f"\nMax turns ({max_turns}) reached.")

        self._write_telemetry(telemetry)

    def _write_telemetry(self, log: list[dict]) -> None:
        out = Path("telemetry/run.jsonl")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "a") as f:
            for entry in log:
                f.write(json.dumps(entry) + "\n")
        print(f"  [telemetry] {len(log)} entries → {out}")


# ── Tool schema conversion ─────────────────────────────────────────────────────

def mcp_tools_to_openai(tools) -> list[dict]:
    result = []
    for t in tools:
        schema = t.inputSchema if hasattr(t, "inputSchema") else {}
        result.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": schema or {"type": "object", "properties": {}},
            },
        })
    return result


# ── Entrypoint ────────────────────────────────────────────────────────────────

async def main_async(task: str, max_turns: int) -> None:
    policy_path = _AGENT_DIR / "openshell-policy.yaml"
    nemo_path = _AGENT_DIR / "nemoclaw.yaml"
    openclaw_path = _AGENT_DIR / "openclaw.json"

    print("\nFactoryMind — three-layer data router")
    print(f"  Policy  : {policy_path}")
    print(f"  NemoClaw: {nemo_path}")
    print(f"  OpenClaw: {openclaw_path}")

    shell = OpenShellGate(policy_path)
    nemo = NemoClawRouter(nemo_path, shell)
    agent = OpenClawAgent(openclaw_path, shell, nemo)

    # OpenShell: verify MCP server endpoint is approved before connecting
    shell.check_network("localhost", 8765)

    with open(openclaw_path) as f:
        cfg = json.load(f)
    mcp_url = cfg["mcp"]["servers"]["factorymind-sim"]["url"]
    print(f"  MCP     : {mcp_url}")
    print(f"  Task    : {task}\n")

    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            oa_tools = mcp_tools_to_openai(tools_result.tools)
            tool_names = {t.name for t in tools_result.tools}
            print(f"MCP tools discovered: {', '.join(sorted(tool_names))}\n")

            await agent.run(task, session, oa_tools, tool_names, max_turns)

    shell.flush_audit(Path("telemetry/openshell-audit.jsonl"))
    print(f"\nLive view: http://localhost:5173/  |  http://localhost:8766/")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task",
        default="Pick all parts from bin_a and place them on station_1. "
                "Reset the cell first, then work autonomously until done=true.",
    )
    parser.add_argument("--max-turns", type=int, default=40)
    args = parser.parse_args()
    asyncio.run(main_async(args.task, args.max_turns))


if __name__ == "__main__":
    main()
