"""Compose assets/cell.xml — dual Menagerie Franka pandas + workcell fixtures.

    python -m factorymind.sim.a.build_cell
"""

from __future__ import annotations

from pathlib import Path

import mujoco

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
PANDA_XML = ASSETS_DIR / "menagerie" / "panda.xml"
CELL_XML = ASSETS_DIR / "cell.xml"

# Floor-mounted arm bases (world frame, metres)
ARM_MOUNTS: dict[int, tuple[list[float], list[float]]] = {
    0: ([-0.22, 0.35, 0.0], [0.7071, 0.0, 0.0, 0.7071]),
    1: ([-0.22, -0.15, 0.0], [0.7071, 0.0, 0.0, 0.7071]),
}

PART_DEFAULTS = {
    "part_1": [0.22, 0.12, 0.46],
    "part_2": [0.25, 0.15, 0.46],
    "part_3": [0.28, 0.18, 0.46],
}


def build_cell_spec() -> mujoco.MjSpec:
    spec = mujoco.MjSpec()
    spec.modelname = "factorymind_cell"
    spec.compiler.meshdir = "menagerie/assets"
    spec.option.timestep = 0.002
    spec.option.gravity = [0, 0, -9.81]
    spec.visual.global_.offwidth = 1280
    spec.visual.global_.offheight = 720

    # Dashboard camera (1280×720 render uses this fixed view)
    wb = spec.worldbody
    wb.add_camera(
        name="dashboard",
        pos=[0.55, 0.0, 1.05],
        xyaxes=[1, 0, 0, 0, 0.85, 0.53],
        fovy=48,
    )
    wb.add_light(pos=[0, 0, 2], dir=[0, 0, -1], diffuse=[0.8, 0.8, 0.8])
    wb.add_geom(
        name="floor",
        type=mujoco.mjtGeom.mjGEOM_PLANE,
        size=[2, 2, 0.05],
        rgba=[0.2, 0.2, 0.2, 1],
    )

    table = wb.add_body(name="table", pos=[0.5, 0.0, 0.4])
    table.add_geom(
        name="table_top",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[0.45, 0.35, 0.02],
        rgba=[0.55, 0.45, 0.35, 1],
    )

    def _site(name: str, pos: list[float], rgba: list[float]) -> None:
        wb.add_site(name=name, pos=pos, size=[0.08, 0.08, 0.01], rgba=rgba)

    _site("bin_a", [0.25, 0.15, 0.44], [0.2, 0.5, 0.8, 0.3])
    wb.add_geom(
        name="bin_a_geom",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0.25, 0.15, 0.42],
        size=[0.1, 0.1, 0.01],
        rgba=[0.2, 0.5, 0.8, 0.6],
        contype=0,
        conaffinity=0,
    )
    _site("station_1", [0.75, 0.15, 0.44], [0.8, 0.5, 0.2, 0.3])
    wb.add_geom(
        name="station_1_geom",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0.75, 0.15, 0.42],
        size=[0.1, 0.1, 0.01],
        rgba=[0.8, 0.5, 0.2, 0.6],
        contype=0,
        conaffinity=0,
    )
    _site("bin_b", [0.25, -0.15, 0.44], [0.2, 0.5, 0.8, 0.3])
    wb.add_geom(
        name="bin_b_geom",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0.25, -0.15, 0.42],
        size=[0.1, 0.1, 0.01],
        rgba=[0.2, 0.5, 0.8, 0.6],
        contype=0,
        conaffinity=0,
    )
    _site("station_2", [0.75, -0.15, 0.44], [0.8, 0.5, 0.2, 0.3])
    wb.add_geom(
        name="station_2_geom",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0.75, -0.15, 0.42],
        size=[0.1, 0.1, 0.01],
        rgba=[0.8, 0.5, 0.2, 0.6],
        contype=0,
        conaffinity=0,
    )

    for part_id, pos in PART_DEFAULTS.items():
        body = wb.add_body(name=part_id, pos=pos)
        body.add_freejoint(name=f"{part_id}_free")
        body.add_geom(
            name=f"{part_id}_geom",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            size=[0.015, 0.015, 0.015],
            mass=0.05,
            rgba=[0.9, 0.85, 0.2, 1],
        )
        body.add_site(name=f"{part_id}_tip", pos=[0, 0, 0], size=[0.012])

    for arm_id, (pos, quat) in ARM_MOUNTS.items():
        panda = mujoco.MjSpec.from_file(str(PANDA_XML))
        for exc in list(panda.excludes):
            panda.delete(exc)
        prefix = f"arm{arm_id}_"
        frame = wb.add_frame(pos=pos, quat=quat)
        spec.attach(panda, prefix=prefix, frame=frame)

    for arm_id in (0, 1):
        hand = spec.body(f"arm{arm_id}_hand")
        hand.add_site(name=f"arm{arm_id}_ee", pos=[0, 0, 0.103], size=[0.01])

    return spec


def main() -> None:
    if not PANDA_XML.exists():
        raise FileNotFoundError(f"Missing Menagerie panda model: {PANDA_XML}")
    spec = build_cell_spec()
    model = spec.compile()
    print(f"Compiled cell — {model.nbody} bodies, {model.njnt} joints, {model.nu} actuators")
    spec.to_file(str(CELL_XML))
    print(f"Wrote {CELL_XML}")


if __name__ == "__main__":
    main()
