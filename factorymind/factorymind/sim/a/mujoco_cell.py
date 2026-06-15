"""MuJoCo cell — dual Franka pandas with interpolated joint control."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import mujoco
import numpy as np

from factorymind.agent.schemas import CellPlan, RobotCommand
from factorymind.sim.a.build_cell import PART_DEFAULTS
from factorymind.sim.a.conveyor import (
    BELT_SPEED,
    BELT_X_END,
    BELT_X_START,
    CONVEYOR_PART_STARTS,
    CONVEYOR_PART_WRAP,
    in_belt_zone,
    part_at_pick_zone,
)
from factorymind.sim.a.pose_lookup import ARM_JOINT_NAMES, apply_arm_qpos, read_arm_qpos
from factorymind.sim.a.frame_export import publish_latest_frame
from factorymind.sim.a.render import CellRenderer, DASHBOARD_HEIGHT, DASHBOARD_WIDTH, default_frames_dir
from factorymind.sim.a.part_catalog import TASK_BY_SCENARIO, is_task_done
from factorymind.sim.a.state import CellState, PartState, RobotState, StationState
from factorymind.sim.a.targets import TARGET_POSES, TARGET_QPOS, TARGET_QPOS_ARM1

Scenario = Literal["default", "sort_green", "misaligned", "empty_bin", "conveyor_feed"]

# Motion is driven by a minimum-jerk trajectory (quintic easing) so each arm
# starts and ends a move at rest — no velocity discontinuity, no lurch.
INTERP_STEPS = 140        # substeps per move; longer = finer joint-space granularity
PLACE_STEPS = 90          # substeps to lower a part onto a station (careful drop)
PHYSICS_SUBSTEPS = 20     # substeps when no arm is moving (settle/conveyor only)
RENDER_EVERY_N = 5        # publish latest.png every N substeps for the live view
LIVE_FRAME_PACE_S = 0.035  # min wall-time between live frames so motion is observable

# Part offsets for optional reset scenarios (metres)
MISALIGNED_OFFSETS = {
    "part_1": (0.06, 0.04, 0.0),
    "part_2": (0.05, -0.03, 0.0),
    "part_3": (-0.04, 0.05, 0.0),
}


def _scene_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "cell.xml"


class MujocoCellEnv:
    """MuJoCo-backed cell with Menagerie Franka arms."""

    num_robots: int

    def __init__(
        self,
        num_robots: int = 2,
        seed: int = 0,
        scenario: Scenario = "default",
    ) -> None:
        path = _scene_path()
        if not path.exists():
            raise FileNotFoundError(f"Missing MJCF scene: {path}")
        self.num_robots = num_robots
        self.seed = seed
        self.scenario: Scenario = scenario
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
        self._arm_goal: list[dict[str, float] | None] = [None, None]
        self._arm_start: list[dict[str, float] | None] = [None, None]
        self._interp_remaining = 0
        self._interp_total = INTERP_STEPS
        self._part_anim: dict[str, dict[str, Any]] = {}
        self._task: str = TASK_BY_SCENARIO.get(scenario, TASK_BY_SCENARIO["default"])
        self._last_frame_t = 0.0
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
        self._arm_goal = [None] * self.num_robots
        self._arm_start = [None] * self.num_robots
        self._interp_remaining = 0
        self._part_anim = {}
        self._task = TASK_BY_SCENARIO.get(self.scenario, TASK_BY_SCENARIO["default"])

        if self.scenario == "empty_bin":
            self._part_at = {}
            self._events.append("scenario_empty_bin")
            self._events.append("empty_bin_diagnosed")
            self._done = True
        elif self.scenario == "conveyor_feed":
            self._part_at = {"part_1": "conveyor", "part_2": "conveyor", "part_3": "conveyor"}
            self._events.append("scenario_conveyor_feed")
        else:
            self._part_at = {"part_1": "bin_a", "part_2": "bin_a", "part_3": "bin_a"}
            if self.scenario == "misaligned":
                self._events.append("scenario_misaligned")

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
            if part_id not in self._part_at:
                continue
            pos = self._part_position(part_id)
            parts.append(PartState.from_id(part_id, pos, self._part_at[part_id]))
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
            task=self._task,
            scenario=self.scenario,
        ).to_dict()

    def set_task(self, instruction: str) -> None:
        """Set the active task (UI prompt). Drives both the oracle's part filter
        and the done-check, so 'pick the yellow only' stops after the yellow cube."""
        cleaned = (instruction or "").strip()
        if cleaned:
            self._task = cleaned

    @property
    def task(self) -> str:
        return self._task

    def list_targets(self) -> list[str]:
        return sorted(TARGET_POSES.keys())

    @property
    def model(self) -> mujoco.MjModel:
        return self._model

    @property
    def data(self) -> mujoco.MjData:
        return self._data

    def render_rgb(self) -> np.ndarray:
        if self._renderer is None:
            self._renderer = CellRenderer(self._model)
        return self._renderer.render_rgb(self._data)

    def save_frame(self, path: str | Path | None = None) -> Path:
        if self._renderer is None:
            self._renderer = CellRenderer(self._model)
        if path is None:
            out = self._frames_dir / f"step_{self._step:04d}.png"
        else:
            out = Path(path)
            if not out.is_absolute():
                out = self._frames_dir / out
        saved = self._renderer.save_png(self._data, out)
        publish_latest_frame(
            saved,
            step=self._step,
            width=DASHBOARD_WIDTH,
            height=DASHBOARD_HEIGHT,
            frames_dir=self._frames_dir,
        )
        return saved

    def step(self, plan: CellPlan) -> dict[str, Any]:
        self._events = []
        self._step += 1

        for cmd in plan.robots:
            if cmd.id < 0 or cmd.id >= self.num_robots:
                self._events.append("invalid_robot_id")
                continue
            self._apply_command(cmd)

        self._simulate_motion_and_physics()
        self._check_collisions()

        parts = [
            {"id": pid, "at": at, "color": PartState.from_id(pid, [0, 0, 0], at).color}
            for pid, at in self._part_at.items()
        ]
        if is_task_done(parts, self._task, self.scenario):
            self._done = True
            if "task_complete" not in self._events:
                self._events.append("task_complete")

        if os.environ.get("FACTORYMIND_SIM_AUTO_FRAME") == "1":
            try:
                self.save_frame()
            except Exception:
                pass

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
            # Capture the arm's current pose as the trajectory start so the
            # min-jerk path is deterministic (not re-read from perturbed physics).
            self._arm_start[cmd.id] = read_arm_qpos(self._model, self._data, cmd.id)
            self._arm_goal[cmd.id] = dict(q)
            self._interp_remaining = INTERP_STEPS
            self._interp_total = INTERP_STEPS
            self._robot_pose[cmd.id] = cmd.target
            return

        if cmd.action == "grip":
            part_id = cmd.target if cmd.target.startswith("part_") else None
            allowed = ("bin_a", "conveyor", part_id) if part_id else ()
            if part_id is None or self._part_at.get(part_id) not in allowed:
                self._events.append("grip_miss")
                return
            if self._part_at.get(part_id) == "conveyor":
                if self._robot_pose[cmd.id] != "conveyor_pick":
                    self._events.append("grip_miss")
                    return
                pos = self._part_position(part_id)
                if not part_at_pick_zone(pos[0]):
                    self._events.append("grip_miss")
                    return
            if self._gripper_closed[cmd.id]:
                self._events.append("gripper_busy")
                return
            self._gripper_closed[cmd.id] = True
            self._holding[cmd.id] = part_id
            self._part_at[part_id] = f"gripper_{cmd.id}"
            self._close_gripper(cmd.id)
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
            self._begin_placement(part_id, station)
            self._open_gripper(cmd.id)
            self._events.append("place_success")

    @staticmethod
    def _min_jerk(tau: float) -> float:
        """Quintic minimum-jerk easing: s(0)=0, s(1)=1, with zero velocity AND
        zero acceleration at both endpoints. This is what makes an arm move
        start and stop smoothly instead of lurching."""
        if tau <= 0.0:
            return 0.0
        if tau >= 1.0:
            return 1.0
        return tau * tau * tau * (10.0 + tau * (-15.0 + 6.0 * tau))

    def _zero_arm_qvel(self, arm_id: int) -> None:
        """Clear arm joint velocities so the integrator doesn't add jitter on
        top of the kinematically-driven trajectory."""
        for jname in ARM_JOINT_NAMES:
            jid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, f"arm{arm_id}_{jname}")
            if jid >= 0:
                dof = int(self._model.jnt_dofadr[jid])
                self._data.qvel[dof] = 0.0

    def _interpolate_arms(self) -> None:
        # Progress fraction across the whole move (0 → 1 over INTERP_STEPS).
        elapsed = self._interp_total - self._interp_remaining
        tau = (elapsed + 1) / float(self._interp_total)
        s = self._min_jerk(tau)

        for i in range(self.num_robots):
            goal = self._arm_goal[i]
            start = self._arm_start[i]
            if goal is None or start is None:
                continue
            blended: dict[str, float] = {}
            for jname in ARM_JOINT_NAMES:
                a = start.get(jname, 0.0)
                b = goal.get(jname, a)
                blended[jname] = a + s * (b - a)
            apply_arm_qpos(
                self._model,
                self._data,
                i,
                blended,
                gripper_open=not self._gripper_closed[i],
            )
            self._zero_arm_qvel(i)
            if tau >= 1.0:
                self._arm_goal[i] = None
                self._arm_start[i] = None

    def _publish_sub_frame(self) -> None:
        """Render current physics state to latest.png for smooth live dashboard view."""
        if self._renderer is None:
            self._renderer = CellRenderer(self._model)
        import shutil
        tmp = self._frames_dir / "_sub.png"
        self._renderer.save_png(self._data, tmp)
        dest = self._frames_dir / "latest.png"
        self._frames_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp, dest)

    def _simulate_motion_and_physics(self) -> None:
        import time
        steps = max(INTERP_STEPS if self._interp_remaining else 0, PHYSICS_SUBSTEPS)
        if self._part_anim:
            steps = max(steps, PLACE_STEPS)
        live = os.environ.get("FACTORYMIND_SIM_AUTO_FRAME") == "1"
        for sub in range(steps):
            if self._interp_remaining > 0:
                self._interpolate_arms()
                self._interp_remaining -= 1
            mujoco.mj_step(self._model, self._data)
            self._sync_gripped_parts()
            self._advance_placements()
            self._advance_conveyor_belt()
            if live and sub % RENDER_EVERY_N == 0:
                # Pace frames in wall-time so the smooth trajectory is actually
                # observable by the dashboard instead of completing in one tick.
                now = time.monotonic()
                wait = LIVE_FRAME_PACE_S - (now - self._last_frame_t)
                if wait > 0:
                    time.sleep(wait)
                self._last_frame_t = time.monotonic()
                try:
                    self._publish_sub_frame()
                except Exception:
                    pass

    def _advance_conveyor_on_body(self, body_id: str, wrap_offset: float, base_y: float, base_z: float) -> None:
        bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        if bid < 0:
            return
        pos = self._data.xpos[bid]
        if not in_belt_zone(float(pos[0]), float(pos[1]), float(pos[2])):
            return
        jnt_adr = int(self._model.body_jntadr[bid])
        if jnt_adr < 0:
            return
        dof_adr = int(self._model.jnt_dofadr[jnt_adr])
        self._data.qvel[dof_adr] = BELT_SPEED
        self._data.qvel[dof_adr + 1] = 0.0
        self._data.qvel[dof_adr + 2] = 0.0
        if float(pos[0]) > BELT_X_END - 0.04:
            wrap_x = BELT_X_START + 0.05 + wrap_offset
            self._set_body_pos(body_id, [wrap_x, base_y, base_z])
            self._data.qvel[dof_adr] = BELT_SPEED

    def _advance_conveyor_belt(self) -> None:
        for part_id, base in CONVEYOR_PART_STARTS.items():
            if self._part_at.get(part_id) != "conveyor":
                continue
            self._advance_conveyor_on_body(
                part_id,
                CONVEYOR_PART_WRAP.get(part_id, 0.0),
                base[1],
                base[2],
            )

    def _close_gripper(self, robot_id: int) -> None:
        for fj in (1, 2):
            jid = mujoco.mj_name2id(
                self._model, mujoco.mjtObj.mjOBJ_JOINT, f"arm{robot_id}_finger_joint{fj}"
            )
            if jid >= 0:
                self._data.qpos[int(self._model.jnt_qposadr[jid])] = 0.0
        act8 = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"arm{robot_id}_actuator8")
        if act8 >= 0:
            self._data.ctrl[act8] = 0.0

    def _open_gripper(self, robot_id: int) -> None:
        for fj in (1, 2):
            jid = mujoco.mj_name2id(
                self._model, mujoco.mjtObj.mjOBJ_JOINT, f"arm{robot_id}_finger_joint{fj}"
            )
            if jid >= 0:
                self._data.qpos[int(self._model.jnt_qposadr[jid])] = 0.04
        act8 = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"arm{robot_id}_actuator8")
        if act8 >= 0:
            self._data.ctrl[act8] = 255.0

    def _apply_home_pose(self) -> None:
        for i in range(self.num_robots):
            table = TARGET_QPOS_ARM1 if i == 1 else TARGET_QPOS
            home = table.get("home", {})
            if home:
                apply_arm_qpos(self._model, self._data, i, home)

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
        if self.scenario == "empty_bin":
            for part_id in PART_DEFAULTS:
                self._set_body_pos(part_id, [0.0, 0.0, -1.0])
            return

        if self.scenario == "conveyor_feed":
            for part_id, pos in CONVEYOR_PART_STARTS.items():
                self._set_body_pos(part_id, list(pos))
            return

        for part_id, base in PART_DEFAULTS.items():
            pos = list(base)
            if self.scenario == "misaligned":
                dx, dy, dz = MISALIGNED_OFFSETS.get(part_id, (0.0, 0.0, 0.0))
                pos[0] += dx
                pos[1] += dy
                pos[2] += dz
            self._set_body_pos(part_id, pos)

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

    def _begin_placement(self, part_id: str, station: str) -> None:
        """Start a careful, min-jerk descent of the part from the gripper down to
        the station surface — instead of teleporting it (which looked like a jump)."""
        site_id = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_SITE, station)
        sp = self._model.site_pos[site_id]
        start = self._part_position(part_id)
        # Land just above the tray pad so the part settles without clipping or bouncing.
        goal = [float(sp[0]), float(sp[1]), float(sp[2]) + 0.008]
        self._part_anim[part_id] = {"start": start, "goal": goal, "step": 0, "total": PLACE_STEPS}

    def _advance_placements(self) -> None:
        """Advance every active placement descent one substep along its min-jerk path."""
        for part_id in list(self._part_anim.keys()):
            anim = self._part_anim[part_id]
            anim["step"] += 1
            tau = anim["step"] / float(anim["total"])
            s = self._min_jerk(tau)
            start, goal = anim["start"], anim["goal"]
            pos = [start[k] + s * (goal[k] - start[k]) for k in range(3)]
            self._set_body_pose_flat(part_id, pos)
            if tau >= 1.0:
                del self._part_anim[part_id]

    def _set_body_pose_flat(self, body_name: str, pos: list[float]) -> None:
        """Set a free body's position upright (identity orientation) and clear its
        velocity, so a placed part descends level and doesn't drift under gravity."""
        bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        jnt_adr = int(self._model.body_jntadr[bid])
        if jnt_adr < 0:
            return
        qpos_adr = int(self._model.jnt_qposadr[jnt_adr])
        self._data.qpos[qpos_adr : qpos_adr + 3] = pos
        self._data.qpos[qpos_adr + 3 : qpos_adr + 7] = [1.0, 0.0, 0.0, 0.0]
        dof = int(self._model.jnt_dofadr[jnt_adr])
        self._data.qvel[dof : dof + 6] = 0.0

    def _find_station(self, ref: str) -> str | None:
        if ref in self._station_status:
            return ref
        return None

    def _check_collisions(self) -> None:
        arm_prefixes = ("arm0_hand", "arm1_hand", "arm0_link7", "arm1_link7")
        arm_geoms = set()
        for name in arm_prefixes:
            bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, name)
            if bid < 0:
                continue
            for gi in range(self._model.ngeom):
                if self._model.geom_bodyid[gi] == bid:
                    arm_geoms.add(gi)
        for i in range(self._data.ncon):
            con = self._data.contact[i]
            g1, g2 = int(con.geom1), int(con.geom2)
            if g1 in arm_geoms or g2 in arm_geoms:
                if "collision" not in self._events:
                    self._events.append("collision")
                break

    def teleport_part(self, part_id: str, target: str) -> dict[str, Any]:
        """Directly move a part to a named zone (bin_a, bin_b, station_1, station_2)."""
        if part_id not in self._part_at:
            return {"ok": False, "error": f"Unknown part: {part_id}"}

        # Release from any gripper
        for i in range(self.num_robots):
            if self._holding[i] == part_id:
                self._holding[i] = None
                self._gripper_closed[i] = False
                self._open_gripper(i)

        _bin_centers: dict[str, list[float]] = {
            "bin_a": [0.25, 0.15, 0.44],
            "bin_b": [0.25, -0.15, 0.44],
        }
        _part_offsets: dict[str, list[float]] = {
            "part_1": [-0.03, -0.03, 0.02],
            "part_2": [0.0, 0.0, 0.02],
            "part_3": [0.03, 0.03, 0.02],
        }

        old_at = self._part_at[part_id]

        if target in ("station_1", "station_2"):
            site_id = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_SITE, target)
            if site_id >= 0:
                sp = self._model.site_pos[site_id]
                self._set_body_pos(part_id, [float(sp[0]), float(sp[1]), float(sp[2]) + 0.025])
            if old_at in self._station_status:
                self._station_status[old_at] = "empty"
            self._station_status[target] = "occupied"
            self._part_at[part_id] = target
        elif target in _bin_centers:
            cx, cy, cz = _bin_centers[target]
            dx, dy, dz = _part_offsets.get(part_id, [0.0, 0.0, 0.02])
            self._set_body_pos(part_id, [cx + dx, cy + dy, cz + dz])
            if old_at in self._station_status:
                self._station_status[old_at] = "empty"
            self._part_at[part_id] = target
        else:
            return {"ok": False, "error": f"Unknown target: {target}"}

        mujoco.mj_forward(self._model, self._data)
        return {"ok": True, "part": part_id, "from": old_at, "target": target}

    # Back-compat for verify_poses
    def _move_arm(self, robot_id: int, qpos: dict[str, float]) -> None:
        apply_arm_qpos(
            self._model,
            self._data,
            robot_id,
            qpos,
            gripper_open=not self._gripper_closed[robot_id],
        )
