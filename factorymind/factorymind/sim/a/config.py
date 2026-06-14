"""Sim engineer config — change backend here without touching shared code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

SimBackend = Literal["mock", "mujoco"]
SimScenario = Literal["default", "misaligned", "empty_bin"]


@dataclass(frozen=True)
class SimConfig:
    backend: SimBackend = "mock"
    num_robots: int = 2
    default_seed: int = 0
    scenario: SimScenario = "default"


def get_config() -> SimConfig:
    backend = os.environ.get("FACTORYMIND_SIM_BACKEND", "mock")
    if backend not in ("mock", "mujoco"):
        backend = "mock"
    scenario = os.environ.get("FACTORYMIND_SIM_SCENARIO", "default")
    if scenario not in ("default", "misaligned", "empty_bin"):
        scenario = "default"
    return SimConfig(backend=backend, scenario=scenario)  # type: ignore[arg-type]
