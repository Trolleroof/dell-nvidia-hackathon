"""Conveyor belt fixture — MJCF geoms + belt-block catalog.

Belt kinematics follow the constant-velocity pattern described in MuJoCo
discussion (google-deepmind/mujoco#547): high-friction surface + scripted
tangential velocity on free bodies in the belt zone.

No external mesh dependency — primitive geoms only (Apache-2.0 / project license).
"""

from __future__ import annotations

# Belt layout (world frame, metres) — runs +X along the front edge of the table
BELT_Y = -0.30
BELT_Z = 0.435
BELT_X_START = 0.12
BELT_X_END = 0.88
BELT_HALF_LENGTH = 0.38
BELT_HALF_WIDTH = 0.06
BELT_SPEED = 0.06  # m/s in +X

BELT_BLOCK_IDS = ("belt_block_1", "belt_block_2", "belt_block_3")

BELT_BLOCK_CATALOG: dict[str, dict[str, str]] = {
    "belt_block_1": {"color": "red", "label": "red block", "shape": "block"},
    "belt_block_2": {"color": "orange", "label": "orange block", "shape": "block"},
    "belt_block_3": {"color": "purple", "label": "purple block", "shape": "block"},
}

BELT_BLOCK_RGBA: dict[str, list[float]] = {
    "red": [0.92, 0.22, 0.18, 1.0],
    "orange": [0.95, 0.55, 0.12, 1.0],
    "purple": [0.55, 0.28, 0.82, 1.0],
}

# Initial block positions on the belt (staggered along +X)
BELT_BLOCK_STARTS: dict[str, list[float]] = {
    "belt_block_1": [0.20, BELT_Y, BELT_Z + 0.012],
    "belt_block_2": [0.38, BELT_Y, BELT_Z + 0.012],
    "belt_block_3": [0.56, BELT_Y, BELT_Z + 0.012],
}

BELT_WRAP_OFFSETS: dict[str, float] = {
    "belt_block_1": 0.0,
    "belt_block_2": 0.18,
    "belt_block_3": 0.36,
}

# Pick station (matches conveyor_pick site x)
BELT_PICK_X = 0.42
BELT_PICK_TOL = 0.06

# Task parts fed on the belt (conveyor_feed scenario)
CONVEYOR_PART_STARTS: dict[str, list[float]] = {
    "part_1": [0.32, BELT_Y, BELT_Z + 0.015],
    "part_2": [0.22, BELT_Y, BELT_Z + 0.015],
    "part_3": [0.12, BELT_Y, BELT_Z + 0.015],
}

CONVEYOR_PART_WRAP: dict[str, float] = {
    "part_1": 0.0,
    "part_2": 0.18,
    "part_3": 0.36,
}


def part_at_pick_zone(x: float) -> bool:
    return abs(x - BELT_PICK_X) <= BELT_PICK_TOL


def rgba_for_belt_block(block_id: str) -> list[float]:
    color = BELT_BLOCK_CATALOG.get(block_id, {}).get("color", "red")
    return BELT_BLOCK_RGBA.get(color, BELT_BLOCK_RGBA["red"])


def in_belt_zone(x: float, y: float, z: float) -> bool:
    return (
        BELT_X_START <= x <= BELT_X_END
        and abs(y - BELT_Y) <= BELT_HALF_WIDTH + 0.02
        and BELT_Z - 0.02 <= z <= BELT_Z + 0.05
    )


def add_conveyor_to_world(wb) -> None:
    """Add static belt frame + sites; free-joint blocks added separately."""
    import mujoco

    cx = (BELT_X_START + BELT_X_END) / 2
    frame = wb.add_body(name="conveyor_frame", pos=[cx, BELT_Y, BELT_Z - 0.015])

    # Rubber belt surface (high friction applied in compiled XML via friction attr)
    frame.add_geom(
        name="conveyor_belt_surface",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0, 0, 0.005],
        size=[BELT_HALF_LENGTH, BELT_HALF_WIDTH, 0.008],
        rgba=[0.12, 0.12, 0.14, 1.0],
        friction=[1.2, 0.005, 0.0001],
    )
    # Side rails
    for side, dy in (("left", BELT_HALF_WIDTH + 0.012), ("right", -(BELT_HALF_WIDTH + 0.012))):
        frame.add_geom(
            name=f"conveyor_rail_{side}",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[0, dy, 0.02],
            size=[BELT_HALF_LENGTH, 0.008, 0.018],
            rgba=[0.35, 0.35, 0.38, 1.0],
            contype=0,
            conaffinity=0,
        )
    # End rollers (visual)
    for end, dx in (("in", -BELT_HALF_LENGTH + 0.02), ("out", BELT_HALF_LENGTH - 0.02)):
        frame.add_geom(
            name=f"conveyor_roller_{end}",
            type=mujoco.mjtGeom.mjGEOM_CYLINDER,
            pos=[dx, 0, 0.012],
            size=[0.025, 0.006],
            rgba=[0.5, 0.5, 0.55, 1.0],
            contype=0,
            conaffinity=0,
        )

    # Visible pick-zone tape on belt (planner sites stay invisible)
    pick_dx = BELT_PICK_X - cx
    frame.add_geom(
        name="conveyor_pick_tape",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[pick_dx, 0, 0.014],
        size=[0.05, BELT_HALF_WIDTH - 0.015, 0.001],
        rgba=[0.92, 0.78, 0.18, 0.75],
        contype=0,
        conaffinity=0,
    )

    for site_name, site_pos in (
        ("conveyor_infeed", [BELT_X_START + 0.05, BELT_Y, BELT_Z + 0.02]),
        ("conveyor_pick", [BELT_PICK_X, BELT_Y, BELT_Z + 0.02]),
        ("conveyor_end", [BELT_X_END - 0.05, BELT_Y, BELT_Z + 0.02]),
    ):
        wb.add_site(
            name=site_name,
            pos=site_pos,
            size=[0.004, 0.004, 0.004],
            rgba=[0.0, 0.0, 0.0, 0.0],
            group=3,
        )


def add_belt_blocks_to_world(wb) -> None:
    import mujoco

    for block_id, pos in BELT_BLOCK_STARTS.items():
        body = wb.add_body(name=block_id, pos=pos)
        body.add_freejoint(name=f"{block_id}_free")
        body.add_geom(
            name=f"{block_id}_geom",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            size=[0.02, 0.02, 0.012],
            mass=0.08,
            rgba=rgba_for_belt_block(block_id),
            friction=[0.9, 0.005, 0.0001],
        )
        body.add_site(name=f"{block_id}_tip", pos=[0, 0, 0], size=[0.015])
