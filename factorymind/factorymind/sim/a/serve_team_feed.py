"""Serve telemetry + sim frames for dashboard Live mode (stdlib only).

    python -m factorymind.sim.a.serve_team_feed
    python -m factorymind.sim.a.serve_team_feed --port 8766

Dashboard URLs:
    http://localhost:8766/telemetry/diffusion_run.jsonl   (isolated diffusion run)
    http://localhost:8766/telemetry/ar_run.jsonl        (isolated AR run — replay side-by-side)
    http://localhost:8766/telemetry/run.jsonl             (live alias)

Sim frame:
    http://localhost:8766/sim/latest.png
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from factorymind.sim.a.frame_export import latest_frame_path
from factorymind.sim.a.telemetry_bridge import default_telemetry_path, telemetry_dir


class FeedHandler(SimpleHTTPRequestHandler):
    telemetry_root: Path = telemetry_dir()
    frames_root: Path = latest_frame_path().parent

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0]
        if clean.startswith("/telemetry/"):
            rel = clean.removeprefix("/telemetry/").lstrip("/")
            return str((self.telemetry_root / rel).resolve())
        if clean.startswith("/sim/"):
            rel = clean.removeprefix("/sim/").lstrip("/")
            return str((self.frames_root / rel).resolve())
        return str((self.telemetry_root / "run.jsonl").resolve())

    def end_headers(self) -> None:
        # Dashboard is a different origin (Vite dev server / static host), so the
        # browser needs CORS to fetch telemetry JSONL. Frames load via <img>
        # (not CORS-gated), but the live feed goes through fetch().
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print(f"[serve] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve telemetry JSONL + sim frames")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    telemetry_dir().mkdir(parents=True, exist_ok=True)
    latest_frame_path().parent.mkdir(parents=True, exist_ok=True)

    handler = partial(FeedHandler, directory=str(telemetry_dir()))
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print(f"Serving on http://{args.host}:{args.port}")
    print(f"  Diffusion run:  http://{args.host}:{args.port}/telemetry/diffusion_run.jsonl")
    print(f"  AR run:         http://{args.host}:{args.port}/telemetry/ar_run.jsonl")
    print(f"  Live alias:     http://{args.host}:{args.port}/telemetry/run.jsonl")
    print(f"  Latest frame:   http://{args.host}:{args.port}/sim/latest.png")
    print(f"  Replay frames:  http://{args.host}:{args.port}/sim/replay/step_0001.png")
    print(f"  (generate feed first: python -m factorymind.sim.a.run_team_feed)")
    if not default_telemetry_path().is_file():
        print("  WARN: run.jsonl missing — run_team_feed not executed yet")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] stopped")


if __name__ == "__main__":
    main()
