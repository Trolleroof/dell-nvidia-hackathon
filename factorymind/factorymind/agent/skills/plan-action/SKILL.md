---
name: plan-action
description: Generate the next CellPlan (C1) for all robots given the current C2 state
user-invocable: false
disable-model-invocation: false

args:
  type: object
  properties:
    state:
      $ref: "../../schemas/c2_state.yaml"
  required: [state]

output:
  $ref: "../../schemas/c1_plan.yaml"
---

## Input

The current C2 state JSON from `read-cell`.

## Your task

Produce a single `CellPlan` JSON object that moves the cell one step closer to task completion (all parts at `station_1`).

## Output schema (C1 — strict)

```json
{
  "plan": "<one-line intent, max 80 chars>",
  "robots": [
    {
      "id": 0,
      "action": "move | grip | release | hold",
      "target": "<named_target>",
      "reason": "<why, one sentence>"
    },
    {
      "id": 1,
      "action": "move | grip | release | hold",
      "target": "<named_target>",
      "reason": "<why, one sentence>"
    }
  ]
}
```

## Planning rules

1. **One robot per target** — never assign two robots the same physical target.
2. **Grip precondition** — robot must be at `above_<target>` (i.e., pose matches the part's location) before gripping.
3. **Release precondition** — robot must hold a part and be at `above_station_1` before releasing to `station_1`.
4. **Task complete** — if `done` is true, emit `hold` at `home` for both robots and set `plan` to `"All parts placed — holding."`.
5. **Error state** — if events contain `collision`, `grip_miss`, or `invalid_target`, set both robots to `hold` at `home` and set `plan` to `"Error recovery — holding for replan."`.
6. **Parallel when safe** — if robot 0 is carrying a part to station_1 and there are still parts in bin_a, robot 1 can move toward bin_a in the same step.

## Output format

Return ONLY the raw JSON object. No markdown fences, no explanation outside the JSON.
