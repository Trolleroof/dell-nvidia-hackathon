---
name: read-cell
description: Read the current cell state (C2 schema) from the sim
user-invocable: false
disable-model-invocation: false

args: {}

output:
  $ref: "../../schemas/c2_state.yaml"
---

Call the `get_cell_state` MCP tool on the `factorymind-sim` server.

Return the full C2 JSON object exactly as received — do not summarize or modify it. The caller (plan-action) needs the raw state.

If the tool call fails, report the error and do not proceed to plan-action.

## What the C2 state contains

- `step` — current sim tick
- `robots[]` — id, pose, gripper (open|closed), holding (part id or null)
- `parts[]` — id, pos [x,y,z], at (bin_a | station_1 | gripper_N | …)
- `stations[]` — id, status (empty | occupied | done)
- `events[]` — events from the last step (empty on first read)
- `done` — true when all parts are at station_1
