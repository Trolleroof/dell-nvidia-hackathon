# Conveyor belt (MJCF primitives)

Open-source style fixture for FactoryMind — **no vendored third-party meshes**.

## Design reference

- Belt velocity pattern: [MuJoCo issue #547](https://github.com/google-deepmind/mujoco/issues/547) (constant-speed conveyor via surface friction + tangential body velocity).
- Robot arms: [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) `franka_emika_panda` (already vendored under `assets/menagerie/`).

## Scene pieces

| Name | Role |
|------|------|
| `conveyor_frame` | Rails + rubber belt surface |
| `conveyor_infeed` / `conveyor_pick` / `conveyor_end` | Planner sites |
| `belt_block_1..3` | Free-moving colored blocks on the belt |

Rebuild after edits:

```bash
python -m factorymind.sim.a.build_cell
python -m factorymind.sim.a.solve_poses
```
