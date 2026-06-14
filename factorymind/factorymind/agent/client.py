"""LLM client abstraction — used by the standalone loop.py (NO-MCP fallback path).

In the primary path (OpenClaw + MCP), the LLM is managed by the OpenClaw runtime;
this file is NOT used. It exists so loop.py can run without OpenClaw installed.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from factorymind.agent.schemas import CellPlan


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class PlanResult:
    plan: CellPlan
    model: str
    latency_ms: float
    retries: int


# ── Base interface ────────────────────────────────────────────────────────────

class LLMClient(ABC):
    """Minimal interface: state dict → CellPlan."""

    @abstractmethod
    def plan(self, state: dict[str, Any], max_retries: int = 1) -> PlanResult:
        """Generate a CellPlan from the current C2 state."""
        ...


# ── Mock client (Mac dev + CI) ────────────────────────────────────────────────

_MOCK_PLAN = {
    "plan": "Mock: robot 0 moves to bin_a, robot 1 holds.",
    "robots": [
        {"id": 0, "action": "move", "target": "bin_a", "reason": "Mock action."},
        {"id": 1, "action": "hold", "target": "home", "reason": "Mock idle."},
    ],
}


class MockClient(LLMClient):
    """Returns a fixed CellPlan — no GPU, no network required."""

    def __init__(self, fixed_plan: dict | None = None, latency_ms: float = 10.0) -> None:
        self._plan = fixed_plan or _MOCK_PLAN
        self._latency_ms = latency_ms

    def plan(self, state: dict[str, Any], max_retries: int = 1) -> PlanResult:
        time.sleep(self._latency_ms / 1000)
        return PlanResult(
            plan=CellPlan.model_validate(self._plan),
            model="mock-llm",
            latency_ms=self._latency_ms,
            retries=0,
        )


# ── OpenAI-compatible client (GB10 with DiffusionGemma or AR Gemma) ──────────

_SYSTEM_PROMPT = """\
You are FactoryMind, an always-on factory floor controller running on a local GB10 superchip.
Output ONLY a single raw JSON object matching the CellPlan schema. No markdown. No explanation.

CellPlan schema:
{
  "plan": "<one-line intent, max 80 chars>",
  "robots": [
    {"id": 0, "action": "move|grip|release|hold", "target": "<named_target>", "reason": "<why>"},
    {"id": 1, "action": "move|grip|release|hold", "target": "<named_target>", "reason": "<why>"}
  ]
}

Valid targets: bin_a, bin_b, station_1, station_2, part_1, part_2, part_3, home.
Always emit exactly one entry per robot. Never invent target names.
"""


class OpenAICompatClient(LLMClient):
    """Calls any OpenAI-compatible endpoint (DiffusionGemma / Gemma4 / vLLM)."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "diffusiongemma-18b",
        api_key: str = "none",
        temperature: float = 0.0,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as e:
            raise ImportError("pip install openai") from e

        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self._temperature = temperature

    def plan(self, state: dict[str, Any], max_retries: int = 1) -> PlanResult:
        user_msg = f"Current cell state:\n{json.dumps(state, indent=2)}\n\nNext CellPlan:"
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        retries = 0
        t0 = time.monotonic()

        while True:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
            )
            raw = response.choices[0].message.content or ""
            latency_ms = (time.monotonic() - t0) * 1000

            try:
                parsed = json.loads(raw.strip())
                cell_plan = CellPlan.model_validate(parsed)
                return PlanResult(
                    plan=cell_plan,
                    model=self._model,
                    latency_ms=latency_ms,
                    retries=retries,
                )
            except Exception:
                if retries >= max_retries:
                    raise
                retries += 1
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        "That output was not valid JSON matching the CellPlan schema. "
                        "Output ONLY the raw JSON object, nothing else."
                    ),
                })


# ── Factory helper ────────────────────────────────────────────────────────────

def make_client(
    mode: str = "mock",
    base_url: str = "http://localhost:8000/v1",
    model: str = "diffusiongemma-18b",
) -> LLMClient:
    """
    mode="mock"   → MockClient (Mac dev / CI)
    mode="local"  → OpenAICompatClient pointing at base_url/model
    """
    if mode == "mock":
        return MockClient()
    if mode == "local":
        return OpenAICompatClient(base_url=base_url, model=model)
    raise ValueError(f"Unknown mode: {mode!r}. Use 'mock' or 'local'.")
