"""Dashboard frame contract — stable `frames/latest.png` for Role C."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from factorymind.sim.a.render import DASHBOARD_HEIGHT, DASHBOARD_WIDTH, default_frames_dir

LATEST_PNG = "latest.png"
LATEST_JSON = "latest.json"


def latest_frame_path(frames_dir: Path | None = None) -> Path:
    return (frames_dir or default_frames_dir()) / LATEST_PNG


def latest_frame_meta_path(frames_dir: Path | None = None) -> Path:
    return (frames_dir or default_frames_dir()) / LATEST_JSON


def publish_latest_frame(
    source: Path,
    *,
    step: int = 0,
    width: int = DASHBOARD_WIDTH,
    height: int = DASHBOARD_HEIGHT,
    frames_dir: Path | None = None,
) -> Path:
    """Copy a rendered PNG to frames/latest.png and write sidecar metadata."""
    out_dir = frames_dir or default_frames_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = out_dir / LATEST_PNG
    shutil.copy2(source, latest)

    meta = {
        "path": str(latest.resolve()),
        "source": str(Path(source).resolve()),
        "step": step,
        "width": width,
        "height": height,
        "updated_at": time.time(),
    }
    meta_path = out_dir / LATEST_JSON
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return latest


def read_latest_frame_meta(frames_dir: Path | None = None) -> dict | None:
    meta_path = latest_frame_meta_path(frames_dir)
    if not meta_path.is_file():
        return None
    return json.loads(meta_path.read_text())
