"""Compose assets/cell.xml — dual Menagerie Franka pandas + workcell fixtures.

    python -m factorymind.sim.a.build_cell
"""

from __future__ import annotations

from pathlib import Path

import mujoco

from factorymind.sim.a.part_catalog import rgba_for_part
from factorymind.sim.a.conveyor import add_conveyor_to_world

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
PANDA_XML = ASSETS_DIR / "menagerie" / "panda.xml"
CELL_XML = ASSETS_DIR / "cell.xml"

# Table-top rear mounts (table top z=0.42). Floor mounts at x=-0.22 caused links
# to clip through the table edge when reaching the conveyor.
TABLE_TOP_Z = 0.42
ARM_MOUNT_QUAT = [0.7071, 0.0, 0.0, 0.7071]  # face +X over the work surface
ARM_MOUNTS: dict[int, tuple[list[float], list[float]]] = {
    0: ([0.08, 0.22, TABLE_TOP_Z], ARM_MOUNT_QUAT),
    1: ([0.08, -0.22, TABLE_TOP_Z], ARM_MOUNT_QUAT),
}

PART_DEFAULTS = {
    "part_1": [0.22, 0.12, 0.46],
    "part_2": [0.25, 0.15, 0.46],
    "part_3": [0.28, 0.18, 0.46],
}

PART_BOX_SIZE = [0.022, 0.022, 0.018]

# IK / planner sites — invisible in viewer + dashboard render (group 3)
SITE_GROUP = 3


def _planner_site(wb, name: str, pos: list[float]) -> None:
    wb.add_site(
        name=name,
        pos=pos,
        size=[0.004, 0.004, 0.004],
        rgba=[0.0, 0.0, 0.0, 0.0],
        group=SITE_GROUP,
    )


def _work_tray(
    wb,
    name: str,
    center: list[float],
    *,
    pad_rgba: list[float],
    rim_rgba: list[float],
) -> None:
    """Flat sorting tray with low rims — no floating debug domes."""
    x, y, z = center
    pad_z = z - 0.018
    wb.add_geom(
        name=f"{name}_pad",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[x, y, pad_z],
        size=[0.085, 0.085, 0.006],
        rgba=pad_rgba,
        contype=0,
        conaffinity=0,
    )
    rim_h = 0.012
    rim_specs = (
        ("north", [x, y + 0.085, pad_z + rim_h]),
        ("south", [x, y - 0.085, pad_z + rim_h]),
        ("east", [x + 0.085, y, pad_z + rim_h]),
        ("west", [x - 0.085, y, pad_z + rim_h]),
    )
    for suffix, pos in rim_specs:
        along_x = suffix in ("east", "west")
        size = [0.006, 0.085, rim_h] if along_x else [0.085, 0.006, rim_h]
        wb.add_geom(
            name=f"{name}_rim_{suffix}",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=pos,
            size=size,
            rgba=rim_rgba,
            contype=0,
            conaffinity=0,
        )
    _planner_site(wb, name, center)


def _arm_pedestal(wb, arm_id: int, mount_pos: list[float]) -> None:
    """Visual base plate on the table — arm attaches at mount_pos."""
    x, y, z = mount_pos
    plate = wb.add_body(name=f"arm{arm_id}_pedestal", pos=[x, y, z - 0.015])
    plate.add_geom(
        name=f"arm{arm_id}_pedestal_plate",
        type=mujoco.mjtGeom.mjGEOM_CYLINDER,
        size=[0.055, 0.015],
        rgba=[0.42, 0.42, 0.45, 1.0],
        contype=0,
        conaffinity=0,
    )


def build_cell_spec() -> mujoco.MjSpec:
    spec = mujoco.MjSpec()
    spec.modelname = "factorymind_cell"
    spec.compiler.meshdir = "menagerie/assets"
    spec.option.timestep = 0.002
    spec.option.gravity = [0, 0, -9.81]
    spec.visual.global_.offwidth = 1280
    spec.visual.global_.offheight = 720
    spec.visual.headlight.ambient = [0.42, 0.42, 0.44]
    spec.visual.headlight.diffuse = [0.55, 0.55, 0.58]
    spec.visual.headlight.specular = [0.12, 0.12, 0.12]

    wb = spec.worldbody
    wb.add_camera(
        name="dashboard",
        pos=[0.55, 0.0, 1.05],
        xyaxes=[1, 0, 0, 0, 0.85, 0.53],
        fovy=48,
    )
    wb.add_light(
        pos=[0.9, 0.35, 1.6],
        dir=[-0.55, -0.15, -1],
        diffuse=[0.85, 0.82, 0.78],
        specular=[0.25, 0.25, 0.25],
    )
    wb.add_light(
        pos=[-0.15, -0.55, 1.3],
        dir=[0.15, 0.35, -1],
        diffuse=[0.35, 0.38, 0.45],
        specular=[0.05, 0.05, 0.05],
    )
    wb.add_geom(
        name="floor",
        type=mujoco.mjtGeom.mjGEOM_PLANE,
        size=[1.2, 1.2, 0.05],
        rgba=[0.32, 0.33, 0.36, 1],
    )
    wb.add_geom(
        name="backdrop",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[-0.08, 0.1, 0.58],
        size=[0.02, 0.82, 0.38],
        rgba=[0.26, 0.28, 0.32, 1],
        contype=0,
        conaffinity=0,
    )

    table = wb.add_body(name="table", pos=[0.5, 0.0, 0.4])
    table.add_geom(
        name="table_top",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[0.45, 0.35, 0.02],
        rgba=[0.5, 0.4, 0.3, 1],
    )
    table.add_geom(
        name="table_skirt",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0, 0, -0.055],
        size=[0.44, 0.34, 0.05],
        rgba=[0.38, 0.32, 0.26, 1],
        contype=0,
        conaffinity=0,
    )

    _work_tray(
        wb,
        "bin_a",
        [0.25, 0.15, 0.44],
        pad_rgba=[0.18, 0.42, 0.72, 0.95],
        rim_rgba=[0.12, 0.28, 0.5, 1.0],
    )
    _work_tray(
        wb,
        "station_1",
        [0.75, 0.15, 0.44],
        pad_rgba=[0.82, 0.55, 0.18, 0.95],
        rim_rgba=[0.58, 0.38, 0.1, 1.0],
    )
    _work_tray(
        wb,
        "bin_b",
        [0.25, -0.15, 0.44],
        pad_rgba=[0.18, 0.42, 0.72, 0.95],
        rim_rgba=[0.12, 0.28, 0.5, 1.0],
    )
    _work_tray(
        wb,
        "station_2",
        [0.75, -0.15, 0.44],
        pad_rgba=[0.82, 0.55, 0.18, 0.95],
        rim_rgba=[0.58, 0.38, 0.1, 1.0],
    )

    for part_id, pos in PART_DEFAULTS.items():
        body = wb.add_body(name=part_id, pos=pos)
        body.add_freejoint(name=f"{part_id}_free")
        body.add_geom(
            name=f"{part_id}_geom",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            size=PART_BOX_SIZE,
            mass=0.06,
            rgba=rgba_for_part(part_id),
        )
        body.add_site(
            name=f"{part_id}_tip",
            pos=[0, 0, 0],
            size=[0.004, 0.004, 0.004],
            rgba=[0, 0, 0, 0],
            group=SITE_GROUP,
        )

    add_conveyor_to_world(wb)

    for arm_id, (pos, quat) in ARM_MOUNTS.items():
        _arm_pedestal(wb, arm_id, pos)
        panda = mujoco.MjSpec.from_file(str(PANDA_XML))
        for exc in list(panda.excludes):
            panda.delete(exc)
        prefix = f"arm{arm_id}_"
        frame = wb.add_frame(pos=pos, quat=quat)
        spec.attach(panda, prefix=prefix, frame=frame)

    for arm_id in (0, 1):
        hand = spec.body(f"arm{arm_id}_hand")
        hand.add_site(name=f"arm{arm_id}_ee", pos=[0, 0, 0.103], size=[0.008])

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
