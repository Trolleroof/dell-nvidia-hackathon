"""GB10 / headless checklist — run on the box (dry-run OK on Mac).

    python -m factorymind.sim.a.run_gb10_check

Writes telemetry/gb10_manifest.json with pass/fail summary.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from factorymind.sim.a.config import SimConfig
from factorymind.sim.a.env_factory import create_cell_env
from factorymind.sim.a.oracle import run_oracle_episode
from factorymind.sim.a.telemetry_bridge import telemetry_dir


def _try_render(backend: str) -> tuple[bool, str]:
    env = os.environ.copy()
    env["FACTORYMIND_SIM_BACKEND"] = "mujoco"
    env["MUJOCO_GL"] = backend
    env["FACTORYMIND_SIM_SKIP_MUJOCO"] = "0"
    print(f"\n--- Headless render (MUJOCO_GL={backend}) ---")
    rc = subprocess.call([sys.executable, "-m", "factorymind.sim.a.render_frame"], env=env)
    if rc != 0:
        return False, f"render_frame failed with MUJOCO_GL={backend}"
    out = Path(__file__).resolve().parent / "frames" / "step_0000.png"
    if not out.is_file() or out.stat().st_size == 0:
        return False, f"no PNG output for MUJOCO_GL={backend}"
    return True, f"{out.name} ({out.stat().st_size} bytes)"


def _scenario_oracle(scenario: str) -> dict:
    cfg = SimConfig(backend="mujoco", scenario=scenario, default_seed=0)  # type: ignore[arg-type]
    max_steps = 160 if scenario == "conveyor_feed" else 60
    final = run_oracle_episode(create_cell_env(cfg), max_steps=max_steps)
    return {
        "scenario": scenario,
        "done": final["done"],
        "step": final["step"],
        "placed": sum(1 for p in final.get("parts", []) if p["at"] == "station_1"),
    }


def main() -> None:
    os.environ["FACTORYMIND_SIM_BACKEND"] = "mujoco"
    started = time.time()
    manifest: dict = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "checks": {},
        "ok": True,
    }

    poses = Path(__file__).resolve().parent / "assets" / "poses.json"
    cell = Path(__file__).resolve().parent / "assets" / "cell.xml"
    if not poses.is_file() or (cell.is_file() and cell.stat().st_mtime > poses.stat().st_mtime):
        print("=== Regenerating poses.json ===")
        rc = subprocess.call([sys.executable, "-m", "factorymind.sim.a.solve_poses"], env=os.environ.copy())
        manifest["checks"]["solve_poses"] = rc == 0
        if rc != 0:
            manifest["ok"] = False
            raise SystemExit("solve_poses failed — run build_cell first")

    steps = [
        ("factorymind.sim.a.smoke_test", "smoke_test"),
        ("factorymind.sim.a.verify_poses", "verify_poses"),
        ("factorymind.sim.a.run_oracle_replay", "oracle_replay"),
    ]

    for module, key in steps:
        print(f"\n=== {key} ===")
        rc = subprocess.call([sys.executable, "-m", module], env=os.environ.copy())
        manifest["checks"][key] = rc == 0
        if rc != 0:
            manifest["ok"] = False
            raise SystemExit(f"{key} failed")

    for scenario in ("sort_green", "misaligned", "empty_bin", "conveyor_feed"):
        print(f"\n=== scenario {scenario} ===")
        result = _scenario_oracle(scenario)
        manifest["checks"][f"scenario_{scenario}"] = result
        print(f"  done={result['done']} step={result['step']} placed={result['placed']}")
        if not result["done"]:
            manifest["ok"] = False
            raise SystemExit(f"scenario {scenario} failed")

    render_ok = False
    render_note = "skipped (non-Linux)"
    if platform.system() == "Linux":
        for gl in ("egl", "osmesa"):
            ok, note = _try_render(gl)
            if ok:
                render_ok = True
                render_note = note
                manifest["checks"]["headless_render"] = {"backend": gl, "detail": note}
                print(f"Headless render OK with MUJOCO_GL={gl} — {note}")
                break
        else:
            manifest["checks"]["headless_render"] = {"backend": None, "detail": "egl and osmesa failed"}
            print("WARN: headless render failed for egl and osmesa")
    else:
        ok, note = _try_render("glfw")
        render_ok = ok
        render_note = note if ok else "glfw failed — on GB10 set MUJOCO_GL=egl"
        manifest["checks"]["headless_render"] = {"backend": "glfw", "detail": render_note, "skipped_on_mac": True}
        print(f"\n--- Headless render (Mac dry-run) — {render_note} ---")

    replay = Path(__file__).resolve().parent / "frames" / "replay"
    n = len(list(replay.glob("*.png"))) if replay.is_dir() else 0
    manifest["checks"]["replay_frames"] = n
    manifest["elapsed_s"] = round(time.time() - started, 2)
    print(f"\n=== GB10 check complete — {n} replay frames ===")
    if n < 10:
        manifest["ok"] = False
        raise SystemExit("Expected ≥ 10 replay PNGs")

    out = telemetry_dir() / "gb10_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Manifest: {out}")


if __name__ == "__main__":
    main()
