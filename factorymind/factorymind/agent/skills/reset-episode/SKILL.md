---
name: reset-episode
description: Reset the assembly cell to the initial pick-and-place scenario
user-invocable: true
disable-model-invocation: false
requires:
  env: []

args:
  type: object
  properties:
    seed:
      type: integer
      default: 0
      description: "Random seed for deterministic episode (default: 0)"
  required: []

output:
  $ref: "../../schemas/reset_result.yaml"
---

Call `reset_cell` on the `factorymind-sim` MCP server.

Optionally accept a `seed` integer from the user (default: 0) for reproducible episodes.

After reset, report a one-line summary:
- How many parts are in `bin_a`
- Robot positions
- Station statuses

Example: `"Cell reset (seed=0): 3 parts in bin_a, robots at home, stations empty."`

Then wait for the user to invoke `run-loop` or issue the next command.
