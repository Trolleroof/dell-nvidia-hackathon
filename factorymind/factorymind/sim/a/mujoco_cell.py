"""MuJoCo cell — physics backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mujoco
import numpy as np

from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.a.render import CellRenderer, default_frames_dir
from factorymind.sim.a.state import CellState, PartState, RobotState, StationState
from factorymind.sim.a.targets import TARGET_POSES, TARGET_QPOS, TARGET_QPOS_ARM1


def _scene_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "cell.xml"


class MujocoCellEnv:
    """MuJoCo-backed cell. Uses precomputed joint targets from targets.py."""

    num_robots: int

    def __init__(self, num_robots: int = 2, seed: int = 0) -> None:
        path = _scene_path()
        if not path.exists():
            raise FileNotFoundError(f"Missing MJCF scene: {path}")
        self.num_robots = num_robots
        self.seed = seed
        self._model = mujoco.MjModel.from_xml_path(str(path))
        self._data = mujoco.MjData(self._model)
        self._rng = np.random.default_rng(seed)
        self._step = 0
        self._events: list[str] = []
        self._done = False
        self._gripper_closed = [False, False]
        self._holding: list[str | None] = [None, None]
        self._robot_pose: list[str] = ["home", "home"]
        self._part_at = {"part_1": "bin_a", "part_2": "bin_a", "part_3": "bin_a"}
        self._station_status = {"station_1": "empty", "station_2": "empty"}
        self._renderer: CellRenderer | None = None
        self._frames_dir = default_frames_dir()
        self.reset(seed)

    def reset(self, seed: int | None = None) -> dict[str, Any]:
        if seed is not None:
            self.seed = seed
            self._rng = np.random.default_rng(seed)
        mujoco.mj_resetData(self._model, self._data)
        self._step = 0
        self._events = []
        self._done = False
        self._gripper_closed = [False] * self.num_robots
        self._holding = [None] * self.num_robots
        self._robot_pose = ["home"] * self.num_robots
        self._part_at = {"part_1": "bin_a", "part_2": "bin_a", "part_3": "bin_a"}
        self._station_status = {"station_1": "empty", "station_2": "empty"}
        self._apply_home_pose()
        self._set_part_positions()
        mujoco.mj_forward(self._model, self._data)
        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        robots = []
        for i in range(self.num_robots):
            robots.append(
                RobotState(
                    id=i,
                    pose=TARGET_POSES.get(self._robot_pose[i], self._robot_pose[i]),
                    gripper="closed" if self._gripper_closed[i] else "open",
                    holding=self._holding[i],
                )
            )
        parts = []
        for part_id in ("part_1", "part_2", "part_3"):
            pos = self._part_position(part_id)
            parts.append(PartState(id=part_id, pos=pos, at=self._part_at[part_id]))
        stations = [
            StationState(id=sid, status=self._station_status[sid])  # type: ignore[arg-type]
            for sid in ("station_1", "station_2")
        ]
        return CellState(
            step=self._step,
            robots=robots,
            parts=parts,
            stations=stations,
            events=list(self._events),
            done=self._done,
        ).to_dict()

    def list_targets(self) -> list[str]:
        return sorted(TARGET_POSES.keys())

    @property
    def model(self) -> mujoco.MjModel:
        return self._model

    @property
    def data(self) -> mujoco.MjData:
        return self._data

    def render_rgb(self) -> np.ndarray:
        """Offscreen RGB frame (H×W×3 uint8) of the current sim state."""
        if self._renderer is None:
            self._renderer = CellRenderer(self._model)
        return self._renderer.render_rgb(self._data)

    def save_frame(self, path: str | Path | None = None) -> Path:
        """Save current state as PNG. Default: sim/a/frames/step_XXXX.png"""
        if self._renderer is None:
            self._renderer = CellRenderer(self._model)
        if path is None:
            out = self._frames_dir / f"step_{self._step:04d}.png"
        else:
            out = Path(path)
            if not out.is_absolute():
                out = self._frames_dir / out
        return self._renderer.save_png(self._data, out)

    def step(self, plan: CellPlan) -> dict[str, Any]:
        self._events = []
        self._step += 1

        for cmd in plan.robots:
            if cmd.id < 0 or cmd.id >= self.num_robots:
                self._events.append("invalid_robot_id")
                continue
            self._apply_command(cmd)

        self._simulate_physics(steps=50)
        self._check_collisions()

        placed = sum(1 for at in self._part_at.values() if at == "station_1")
        if placed >= 3:
            self._done = True
            if "task_complete" not in self._events:
                self._events.append("task_complete")

        return self.get_state()

    def _apply_command(self, cmd: RobotCommand) -> None:
        if cmd.action == "hold":
            return

        if cmd.action == "move":
            table = TARGET_QPOS_ARM1 if cmd.id == 1 else TARGET_QPOS
            q = table.get(cmd.target)
            if q is None:
                self._events.append("invalid_target")
                return
            self._move_arm(cmd.id, q)
            self._robot_pose[cmd.id] = cmd.target
            return

        if cmd.action == "grip":
            part_id = cmd.target if cmd.target.startswith("part_") else None
            if part_id is None or self._part_at.get(part_id) not in ("bin_a", part_id):
                self._events.append("grip_miss")
                return
            if self._gripper_closed[cmd.id]:
                self._events.append("gripper_busy")
                return
            self._gripper_closed[cmd.id] = True
            self._holding[cmd.id] = part_id
            self._part_at[part_id] = f"gripper_{cmd.id}"
            self._events.append("pick_success")
            return

        if cmd.action == "release":
            if not self._gripper_closed[cmd.id] or self._holding[cmd.id] is None:
                self._events.append("release_empty")
                return
            station = self._find_station(cmd.target)
            if station is None:
                self._events.append("invalid_release_target")
                return
            part_id = self._holding[cmd.id]
            assert part_id is not None
            self._gripper_closed[cmd.id] = False
            self._holding[cmd.id] = None
            self._part_at[part_id] = station
            self._station_status[station] = "occupied"
            self._place_part_on_station(part_id, station)
            self._events.append("place_success")

    def _move_arm(self, robot_id: int, qpos: dict[str, float]) -> None:
        for axis, value in qpos.items():
            full = f"arm{robot_id}_{axis}"
            jid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, full)
            if jid < 0:
                continue
            adr = self._model.jnt_qposadr[jid]
            self._data.qpos[adr] = value
            act_name = f"act_{full}"
            aid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_ACTUATOR, act_name)
            if aid >= 0:
                self._data.ctrl[aid] = value
        mujoco.mj_forward(self._model, self._data)

    def _apply_home_pose(self) -> None:
        for i in range(self.num_robots):
            table = TARGET_QPOS_ARM1 if i == 1 else TARGET_QPOS
            home = table.get("home", {})
            if home:
                self._move_arm(i, home)

    def _simulate_physics(self, steps: int = 50) -> None:
        for _ in range(steps):
            mujoco.mj_step(self._model, self._data)
            self._sync_gripped_parts()

    def _sync_gripped_parts(self) -> None:
        for i in range(self.num_robots):
            part_id = self._holding[i]
            if part_id is None:
                continue
            ee = self._ee_position(i)
            self._set_body_pos(part_id, ee)

    def _ee_position(self, robot_id: int) -> list[float]:
        site_id = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_SITE, f"arm{robot_id}_ee")
        pos = self._data.site_xpos[site_id]
        return [float(pos[0]), float(pos[1]), float(pos[2])]

    def _part_position(self, part_id: str) -> list[float]:
        bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, part_id)
        pos = self._data.xpos[bid]
        return [float(pos[0]), float(pos[1]), float(pos[2])]

    def _set_part_positions(self) -> None:
        defaults = {
            "part_1": (0.22, 0.12, 0.46),
            "part_2": (0.25, 0.15, 0.46),
            "part_3": (0.28, 0.18, 0.46),
        }
        for part_id, (x, y, z) in defaults.items():
            self._set_body_pos(part_id, [x, y, z])

    def _set_body_pos(self, body_name: str, pos: list[float]) -> None:
        bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        jnt_adr = self._model.body_jntadr[bid]
        if jnt_adr < 0:
            return
        qpos_adr = self._model.jnt_qposadr[jnt_adr]
        self._data.qpos[qpos_adr : qpos_adr + 3] = pos

    def _place_part_on_station(self, part_id: str, station: str) -> None:
        site_id = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_SITE, station)
        sp = self._model.site_pos[site_id]
        self._set_body_pos(part_id, [float(sp[0]), float(sp[1]), float(sp[2]) + 0.02])

    def _find_station(self, ref: str) -> str | None:
        if ref in self._station_status:
            return ref
        return None

    def _check_collisions(self) -> None:
        """Emit collision events when arm geoms contact table or parts."""
        arm_geoms = {
            mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_GEOM, n)
            for n in ("arm0_gripper", "arm1_gripper", "arm0_link", "arm1_link")
        }
        for i in range(self._data.ncon):
            con = self._data.contact[i]
            g1, g2 = int(con.geom1), int(con.geom2)
            if g1 in arm_geoms or g2 in arm_geoms:
                if "collision" not in self._events:
                    self._events.append("collision")
                break
