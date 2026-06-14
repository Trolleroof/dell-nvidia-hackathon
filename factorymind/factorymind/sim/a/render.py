"""Offscreen MuJoCo rendering — 720p dashboard camera for cell scenes."""

from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np

DASHBOARD_WIDTH = 1280
DASHBOARD_HEIGHT = 720
DASHBOARD_CAMERA = "dashboard"

# Framed overview of the full cell (free camera — XML fixed cam quat was misaligned)
DASHBOARD_LOOKAT = (0.45, 0.0, 0.45)
DASHBOARD_DISTANCE = 1.35
DASHBOARD_ELEVATION = -28.0
DASHBOARD_AZIMUTH = 132.0

# Legacy default (kept for callers that omit size)
DEFAULT_WIDTH = DASHBOARD_WIDTH
DEFAULT_HEIGHT = DASHBOARD_HEIGHT


def default_frames_dir() -> Path:
    return Path(__file__).resolve().parent / "frames"


class CellRenderer:
    """Headless renderer for assets/cell.xml — fixed dashboard camera when present."""

    def __init__(
        self,
        model: mujoco.MjModel,
        width: int = DASHBOARD_WIDTH,
        height: int = DASHBOARD_HEIGHT,
        camera: str | int | None = DASHBOARD_CAMERA,
    ) -> None:
        self._model = model
        self._renderer = mujoco.Renderer(model, height, width)
        self._camera = camera
        cam_id = -1
        if isinstance(camera, str):
            cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, camera)
        elif isinstance(camera, int):
            cam_id = camera
        self._camera_id = cam_id if cam_id >= 0 else None
        self._free_camera = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(model, self._free_camera)
        self._free_camera.lookat[:] = DASHBOARD_LOOKAT
        self._free_camera.distance = DASHBOARD_DISTANCE
        self._free_camera.elevation = DASHBOARD_ELEVATION
        self._free_camera.azimuth = DASHBOARD_AZIMUTH
        self._use_free_camera = camera == DASHBOARD_CAMERA or cam_id < 0

    def render_rgb(self, data: mujoco.MjData) -> np.ndarray:
        """Return H×W×3 uint8 RGB array."""
        if self._use_free_camera:
            self._renderer.update_scene(data, camera=self._free_camera)
        elif self._camera_id is not None:
            self._renderer.update_scene(data, camera=self._camera_id)
        else:
            self._renderer.update_scene(data)
        return self._renderer.render()

    def save_png(self, data: mujoco.MjData, path: Path) -> Path:
        """Render current state and write a PNG file."""
        try:
            import imageio.v3 as iio
        except ImportError as exc:
            raise ImportError("pip install imageio for PNG export") from exc

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rgb = self.render_rgb(data)
        iio.imwrite(path, rgb)
        return path


def render_scene_to_png(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    path: Path | str,
    width: int = DASHBOARD_WIDTH,
    height: int = DASHBOARD_HEIGHT,
    camera: str | int | None = DASHBOARD_CAMERA,
) -> Path:
    """One-shot render helper."""
    renderer = CellRenderer(model, width=width, height=height, camera=camera)
    return renderer.save_png(data, Path(path))
