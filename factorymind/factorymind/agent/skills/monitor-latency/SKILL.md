---
name: monitor-latency
description: Track and report plan-generation latency — DiffusionGemma vs AR baseline
user-invocable: true
disable-model-invocation: true
requires:
  env: []

args:
  type: object
  properties:
    log:
      type: array
      description: "Latency log from run-loop output. If omitted, reads from session memory."
      items:
        $ref: "../../schemas/latency_entry.yaml"
  required: []

output:
  $ref: "../../schemas/latency_report.yaml"
---

## What this skill tracks

After each `plan-action` call inside `run-loop`, the loop records:

```json
{
  "step": 7,
  "model": "diffusiongemma-18b",
  "latency_ms": 142,
  "retries": 0,
  "success": true
}
```

These entries are stored in session memory under `latency_log`.

## When invoked by the user

Print a compact latency report:

```
Model                  Steps  Avg ms  Min ms  Max ms  Retries
diffusiongemma-18b     12     143     98      201     0
gemma4-ar              12     891     712     1043    1
```

Highlight the speedup ratio: `"DiffusionGemma was X.Xx faster than AR Gemma on this episode."`

## Add more behavior here

This skill is the right place to add:
- Live streaming chart (pipe latency_log to a WebSocket for the dashboard)
- Side-by-side episode comparison (same seed, two models, compare step counts + latency)
- CSV export for the demo write-up
