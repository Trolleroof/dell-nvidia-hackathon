"""Offscreen MuJoCo rendering — PNG frames from the cell scene."""

from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480


def default_frames_dir() -> Path:
    return Path(__file__).resolve().parent / "frames"


class CellRenderer:
    """Headless renderer for assets/cell.xml scenes."""

    def __init__(
        self,
        model: mujoco.MjModel,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ) -> None:
        self._model = model
        self._renderer = mujoco.Renderer(model, height, width)

    def render_rgb(self, data: mujoco.MjData) -> np.ndarray:
        """Return H×W×3 uint8 RGB array."""
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
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> Path:
    """One-shot render helper."""
    renderer = CellRenderer(model, width=width, height=height)
    return renderer.save_png(data, Path(path))
