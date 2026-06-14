"""Load the MuJoCo cell scene in the interactive viewer.

Run:
    python -m factorymind.sim.a.view_scene
"""

from __future__ import annotations

from pathlib import Path

import mujoco
import mujoco.viewer


def scene_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "cell.xml"


def main() -> None:
    path = scene_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing scene: {path}")

    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)

    print(f"Loaded: {path}")
    print(f"  bodies={model.nbody} joints={model.njnt} actuators={model.nu}")
    print("Close the viewer window to exit.")

    mujoco.viewer.launch(model, data)


if __name__ == "__main__":
    main()
