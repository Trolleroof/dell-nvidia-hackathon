"""Sim engineer config — change backend here without touching shared code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

SimBackend = Literal["mock", "mujoco"]


@dataclass(frozen=True)
class SimConfig:
    backend: SimBackend = "mock"
    num_robots: int = 2
    default_seed: int = 0


def get_config() -> SimConfig:
    backend = os.environ.get("FACTORYMIND_SIM_BACKEND", "mock")
    if backend not in ("mock", "mujoco"):
        backend = "mock"
    return SimConfig(backend=backend)  # type: ignore[arg-type]
