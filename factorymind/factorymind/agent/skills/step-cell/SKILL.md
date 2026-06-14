---
name: step-cell
description: Apply a CellPlan to the sim and advance one control tick
user-invocable: false
disable-model-invocation: false

args:
  type: object
  properties:
    plan_json:
      type: string
      description: "JSON-serialized CellPlan — see schemas/c1_plan.yaml for structure"
  required: [plan_json]

output:
  $ref: "../../schemas/c2_state.yaml"
---

## Input

The CellPlan object produced in the Plan phase (from `plan-action` reasoning).
This is a structured object — NOT yet a string.

## Steps

1. Serialize the CellPlan object to a compact JSON string (no extra whitespace required).
2. Call MCP tool `step_cell` on server `factorymind-sim` with argument:
   `plan_json = <the JSON string from step 1>`.
2. Receive the updated C2 state.
3. Inspect `events`:
   - `pick_success` or `place_success` → log to user (one line).
   - `task_complete` → log to user and signal the loop to stop.
   - `collision`, `invalid_target`, `grip_miss`, `gripper_busy` → log the error. Do **not** continue — trigger a re-read and replan.
   - `invalid_robot_id` → this is a bug in plan-action. Log and stop.
4. Return the new C2 state to the caller.

## On parse failure

If `step_cell` rejects the plan (malformed JSON or schema mismatch), log the error, hold all robots, and call `read-cell` again before planning a new step. Do not retry the same bad plan.
