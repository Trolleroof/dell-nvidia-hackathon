---
name: run-loop
description: Run the full read → plan → step control loop until the task is complete
user-invocable: true
disable-model-invocation: false
requires:
  env: []

args:
  type: object
  properties:
    max_steps:
      type: integer
      default: 100
      minimum: 1
      description: "Safety ceiling — stop after this many steps even if not done"
    model:
      type: string
      default: "diffusiongemma-18b"
      description: "Model name to use for plan-action (overrides openclaw.json default)"
    verbose:
      type: boolean
      default: false
      description: "If true, print each CellPlan JSON as it is generated"
  required: []

output:
  $ref: "../../schemas/loop_stats.yaml"
---

This is the main entry point for the FactoryMind controller demo.

## How this skill works in OpenClaw

You (the agent) drive the loop directly. Each iteration you call MCP tools on the
`factorymind-sim` server. Use the `read-cell`, `plan-action`, and `step-cell` skill
instructions as guides for each phase — they are not function calls, they are
instructions you follow in sequence.

## Loop — repeat until `done` is true or `max_steps` is reached

### Phase 1 — Read (follow `read-cell` skill)
Call MCP tool `get_cell_state` on server `factorymind-sim`.
Receive the C2 state object. If `done` is true, stop immediately.

### Phase 2 — Plan (follow `plan-action` skill)
Using the C2 state now in context, reason and produce a CellPlan JSON object.
Record wall-clock time from start of reasoning to valid JSON parse — this is the
plan latency for this step. Store it in session memory under `latency_log`.

### Phase 3 — Step (follow `step-cell` skill)
Serialize the CellPlan object to a JSON string.
Call MCP tool `step_cell` on server `factorymind-sim` with argument
`plan_json = <that JSON string>`.
Inspect the returned `events` array:
- `pick_success` / `place_success` / `task_complete` → log to user (one line).
- `collision`, `grip_miss`, `invalid_target`, `gripper_busy` → log the error,
  then go back to Phase 1 immediately (replan — do not retry the same plan).
- `invalid_robot_id` → stop and report a bug in the plan.

## Parameters (optional, from user)

- `max_steps` (int, default 100) — safety ceiling to prevent infinite loops.
- `model` (string) — you may note which model you are using in latency_log entries.
- `verbose` (bool, default false) — if true, print each CellPlan JSON when generated.

## On completion

Report a summary:
- Total steps taken
- Total wall-clock time
- Average plan latency (ms)
- Which model was used

Example: `"Task complete in 12 steps (8.3s). Avg plan latency: 143ms [diffusiongemma-18b]."`

## Add more behavior here

This skill is the right place to add:
- Multimodal input (pass a camera frame into the Plan phase for vision-based replanning)
- Second-robot parallelism logic
- Live latency comparison (run two models simultaneously on the same state)
