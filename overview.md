# FactoryMind — Project Overview

FactoryMind is a Dell x NVIDIA GB10 hackathon project: a local factory-cell control room where natural-language operator commands drive a two-arm assembly simulation, with live telemetry and dashboard feedback.

The project demonstrates the core thesis that factory-floor intelligence should run locally: operational data stays on the box, control decisions avoid cloud latency, and a persistent agent can keep a robotic cell moving safely.

---

## Current Demo

The demo that is working today is a local, live simulation stack:

1. A browser dashboard runs at `http://localhost:3000/`.
2. A sim command bridge runs at `http://localhost:8765`.
3. A telemetry/file server runs at `http://localhost:8766`.
4. The dashboard sends operator commands to the backend.
5. The backend advances the cell using the deterministic oracle policy.
6. Telemetry is written to `telemetry/run.jsonl`.
7. The dashboard displays live state, activity, and a modern organic/natural UI.

The current local demo uses the `mock` simulation backend unless MuJoCo is installed and selected. The mock backend is intentional: it gives a stable, no-GPU demo path on a laptop.

---

## What Has Been Built

### Simulation

Simulation code lives in:

```text
factorymind/factorymind/sim/a/
```

Completed pieces:

- `MockCellEnv` for deterministic local development with no MuJoCo dependency.
- `MujocoCellEnv` for physics-backed cell simulation when `mujoco` is installed.
- Dual-arm assembly-cell model and MuJoCo assets.
- Deterministic oracle planner for safe pick-and-place behavior.
- Structured C2 cell state: robots, parts, stations, events, task, scenario.
- Scenario support:
  - `default`
  - `sort_green`
  - `misaligned`
  - `empty_bin`
  - `conveyor_feed`
- Conveyor-feed scenario with parts moving through a pick zone.
- Empty-bin diagnosis scenario that terminates cleanly with `empty_bin_diagnosed`.
- Frame export contract for dashboard frames:
  - `frames/latest.png`
  - `frames/latest.json`
  - replay frames under `frames/replay/`
- Smoke tests for mock scenarios and clean MuJoCo skipping when MuJoCo is not installed.

Important files:

```text
factorymind/factorymind/sim/a/cell.py              # mock backend
factorymind/factorymind/sim/a/mujoco_cell.py       # MuJoCo backend
factorymind/factorymind/sim/a/oracle.py            # deterministic planner
factorymind/factorymind/sim/a/state.py             # C2 state schema
factorymind/factorymind/sim/a/mcp_server.py        # MCP + HTTP command bridge
factorymind/factorymind/sim/a/run_team_feed.py     # telemetry/replay generation
factorymind/factorymind/sim/a/serve_team_feed.py   # telemetry/frame server
```

### Backend / Command Bridge

The sim backend exposes both MCP tools and browser-friendly HTTP routes.

Primary local command endpoint:

```text
POST http://localhost:8765/command
```

Example payload:

```json
{
  "instruction": "Run five safe assembly steps",
  "steps": 5
}
```

Typical response:

```json
{
  "ok": true,
  "task": "Run five safe assembly steps",
  "steps_run": 5,
  "done": false,
  "executed": [
    {
      "step": 1,
      "action": "r0 move bin_a; r1 hold home",
      "events": []
    }
  ],
  "feed": "http://localhost:8766/telemetry/run.jsonl"
}
```

Other backend features:

- `reset_cell(seed, scenario)` for switching sim layouts.
- `get_cell_state()` for structured state reads.
- `step_cell(plan_json)` for applying validated `CellPlan` actions.
- `list_targets()` returns valid named targets.
- `/sim/state` is used by the frontend for interactive part controls.
- `/sim/stream.mjpg` is used by the frontend when a live MuJoCo stream is available.

### Frontend Dashboard

Dashboard code lives in:

```text
factorymind/factorymind/demo/dashboard/
```

Stack:

- React
- TypeScript
- Vite
- Tailwind CSS

The dashboard has been redesigned into a modern, poppy, organic/natural control room:

- Warm paper background.
- Subtle grain texture.
- Moss/clay/sun/blue color palette.
- Fraunces + Nunito typography.
- Soft organic blobs and tactile card shapes.
- Pill buttons and scenario controls.
- Live sim panel.
- Operator command channel.
- Telemetry metrics and activity log.
- Scenario picker.
- Drag/drop part controls when backend state is available.

Important files:

```text
factorymind/factorymind/demo/dashboard/src/App.tsx
factorymind/factorymind/demo/dashboard/src/components/Header.tsx
factorymind/factorymind/demo/dashboard/src/components/AgentSimPage.tsx
factorymind/factorymind/demo/dashboard/src/components/CellView.tsx
factorymind/factorymind/demo/dashboard/src/components/Telemetry.tsx
factorymind/factorymind/demo/dashboard/src/hooks/useTelemetry.ts
factorymind/factorymind/demo/dashboard/src/index.css
factorymind/factorymind/demo/dashboard/tailwind.config.js
```

---

## Architecture

```text
Operator
  |
  v
React/Vite Dashboard (:3000)
  |
  | POST /command
  v
FactoryMind Sim Server (:8765)
  |
  | oracle_plan(state) -> CellPlan
  v
MockCellEnv or MujocoCellEnv
  |
  | telemetry/run.jsonl
  | frames/latest.png or stream.mjpg
  v
Telemetry + Frame Server (:8766)
  |
  v
Dashboard live view
```

Contracts:

- **C1 — CellPlan:** action schema accepted by the sim.
- **C2 — Cell State:** structured state returned by the sim.
- **C5 — Telemetry JSONL:** live/replay feed consumed by the dashboard.

The current live local path uses the deterministic oracle for safe, repeatable behavior. The intended GB10 path swaps the oracle/mock planning layer for local model planning through DiffusionGemma or Gemma AR while keeping the same schemas and sim tools.

---

## How It Works

FactoryMind is built around one loop: observe the cell, choose the next safe action, step the sim, publish telemetry, and update the dashboard.

### Runtime Loop

1. **Operator intent enters the dashboard.**  
   The user types a command such as `Run five safe assembly steps` or chooses a scenario from the UI.

2. **Dashboard calls the command bridge.**  
   The React app sends a JSON request to `POST http://localhost:8765/command`.

3. **Backend reads the current cell state.**  
   The sim exposes structured C2 state: robot poses, gripper state, held objects, part positions, station status, latest events, current task, and scenario.

4. **Planner chooses an action block.**  
   In the local stable demo, `oracle_plan(state)` creates the next valid `CellPlan`. On the intended GB10 path, this planner can be replaced by DiffusionGemma or Gemma AR while keeping the same `CellPlan` schema.

5. **Sim validates and applies the action.**  
   The sim accepts only structured actions such as `move`, `grip`, `release`, and `hold` against named targets like `bin_a`, `station_1`, `part_1`, or `conveyor_pick`.

6. **Events are produced.**  
   Example events include `pick_success`, `place_success`, `grip_miss`, `collision`, `task_complete`, `scenario_misaligned`, and `empty_bin_diagnosed`.

7. **Telemetry is written.**  
   Each step becomes a JSONL row in `telemetry/run.jsonl`. The dashboard polls this feed through the telemetry server on `:8766`.

8. **Dashboard refreshes live.**  
   The UI updates the sim panel, step count, health indicator, activity log, and latency/decision metrics.

### Data Flow

```text
Operator command
  -> Dashboard form
  -> POST /command
  -> get current C2 state
  -> oracle/model creates CellPlan
  -> sim.step(CellPlan)
  -> events + updated state
  -> telemetry/run.jsonl
  -> dashboard poll/update
```

### Action Schema

A `CellPlan` is the structured action block used to move the cell one step.

Conceptually:

```json
{
  "plan": "Robot 0 grips part_1 from bin_a.",
  "robots": [
    {
      "id": 0,
      "action": "grip",
      "target": "part_1",
      "reason": "Close gripper once aligned."
    },
    {
      "id": 1,
      "action": "hold",
      "target": "home",
      "reason": "Stand clear."
    }
  ]
}
```

Supported robot actions:

| Action | What it does |
|---|---|
| `move` | Moves a robot to a named target pose. |
| `grip` | Attempts to pick a part. Emits `pick_success` or `grip_miss`. |
| `release` | Places the held part at a station. Emits `place_success` or `release_empty`. |
| `hold` | Keeps a robot safely idle for the step. |

Named targets include:

```text
home
bin_a
bin_b
station_1
station_2
part_1
part_2
part_3
conveyor_pick
```

---

## Feature Reference

### Dashboard Features

| Feature | What it does | Why it matters |
|---|---|---|
| **Control Room UI** | Main browser interface at `localhost:3000`. | Gives judges/operators a single place to see and control the demo. |
| **Run / Pause** | Starts or stops automatic step requests to the backend. | Lets the demo run continuously or pause for explanation. |
| **Reset** | Clears dashboard telemetry state and resets the local view. | Useful between demo attempts. |
| **Speed Slider** | Changes how frequently the UI asks the backend for another step. | Makes the sim feel live without needing high-frequency physics. |
| **Scenario Picker** | Switches between `default`, `sort_green`, `misaligned`, `conveyor_feed`, and `empty_bin`. | Shows the same architecture handling different factory conditions. |
| **Operator Channel** | Chat-style command input for natural-language instructions. | Makes the agent story visible: human intent enters as plain language. |
| **Live Sim Panel** | Shows either live MuJoCo frames/stream or the animated fallback cell. | Gives the audience a visual object to follow. |
| **Cell Stats** | Shows current step, latest event, and placed part count. | Makes progress legible at a glance. |
| **Telemetry Metrics** | Displays latest latency/model decision data from the JSONL feed. | Connects the sim story to model/runtime performance. |
| **Activity Log** | Lists recent decisions and events. | Shows the loop is actually doing step-by-step work. |
| **Drag/Drop Part Controls** | Lets a user move parts between zones when backend state is available. | Useful for testing scenarios and showing interactive recovery. |
| **Modern Organic Theme** | Warm paper texture, moss/clay palette, organic cards, pill controls. | Makes the demo feel polished, memorable, and less like a raw engineering console. |

### Backend Features

| Feature | What it does | Important file |
|---|---|---|
| **MCP Server** | Exposes sim tools for agent clients. | `sim/a/mcp_server.py` |
| **HTTP Command Bridge** | Lets the browser call the sim directly with `POST /command`. | `sim/a/mcp_server.py` |
| **Scenario Endpoint** | Lets the dashboard swap task/layout presets. | `sim/a/mcp_server.py` |
| **State Endpoint** | Lets the dashboard poll current parts/robots. | `sim/a/mcp_server.py` |
| **Telemetry Writer** | Converts sim steps into C5 JSONL rows. | `sim/a/telemetry_bridge.py` |
| **Telemetry Server** | Serves telemetry and frames to the browser. | `sim/a/serve_team_feed.py` |
| **Oracle Planner** | Generates safe deterministic `CellPlan` actions. | `sim/a/oracle.py` |
| **Smoke Test** | Verifies scenarios and skips MuJoCo cleanly when missing. | `sim/a/smoke_test.py` |

### Simulation Features

| Feature | What it does | Notes |
|---|---|---|
| **Mock Backend** | Pure-Python deterministic simulation. | Works on laptops without MuJoCo or GPU. |
| **MuJoCo Backend** | Physics/rendering backend using MJCF assets. | Requires `mujoco` Python package and GL/EGL setup for rendering. |
| **Dual Arms** | Represents two robot arms with coordinated commands. | Oracle currently uses robot 0 for most task work and robot 1 as safe hold. |
| **Parts** | `part_1`, `part_2`, `part_3` with metadata such as color/label/shape. | Enables structured tasks like sorting green boxes. |
| **Stations** | Placement targets such as `station_1` and `station_2`. | Used to evaluate task completion. |
| **Conveyor** | Feeds parts through `conveyor_pick`. | Demonstrates a more factory-like flow. |
| **Misalignment** | Starts parts offset from their normal positions. | Demonstrates recovery behavior. |
| **Empty Bin** | Starts with no parts and emits `empty_bin_diagnosed`. | Demonstrates diagnosis rather than endless failed picking. |
| **Frame Export** | Writes latest/replay PNG metadata for dashboard consumption. | Used by MuJoCo/replay paths. |

### Scenario Behavior

| Scenario | What happens | Completion condition |
|---|---|---|
| `default` | Pick all parts from `bin_a` and place them at `station_1`. | All parts are at `station_1`. |
| `sort_green` | Only green parts are task-relevant. | Green part is at `station_1`. |
| `misaligned` | Parts start offset from normal bin positions. | Oracle approaches parts directly and places them. |
| `conveyor_feed` | Parts move along the conveyor toward `conveyor_pick`. | Parts are picked from the belt and placed at `station_1`. |
| `empty_bin` | No parts start in the bin. | Backend diagnoses the empty bin and stops cleanly. |

### Telemetry Fields

| Field | Meaning |
|---|---|
| `ts` | Timestamp for the decision row. |
| `step` | Sim control step. |
| `model` | Source model/profile, such as diffusion, AR, mock, or oracle. |
| `latency_ms` | Wall-clock time associated with the decision. |
| `ttft_ms` | Time to first token when using a model endpoint. |
| `prompt_tokens` | Prompt token count. |
| `completion_tokens` | Completion token count. |
| `parsed_ok` | Whether the plan parsed/validated successfully. |
| `retries` | Number of parse/validation retries. |
| `action_summary` | Human-readable summary of the applied action. |
| `sim_event` | Main event emitted by the sim. |
| `frame_url` | Optional frame path for replay/live visual sync. |

---

## Local Run Commands

Run from the repository root unless noted.

### 1. Python Smoke Test

```bash
cd /Users/emanschool/dell-nvidia-hackathon/factorymind
PYTHONDONTWRITEBYTECODE=1 python3 -m factorymind.sim.a.smoke_test
```

Expected on a laptop without MuJoCo:

```text
OK [mock] ...
OK [mock sort_green] ...
OK [mock misaligned] ...
OK [mock empty_bin] ...
OK [mock conveyor_feed] ...
SKIP [mujoco] — pip install mujoco to run physics smoke test
```

### 2. Sim Command Bridge

```bash
cd /Users/emanschool/dell-nvidia-hackathon/factorymind
PYTHONDONTWRITEBYTECODE=1 FACTORYMIND_SIM_BACKEND=mock \
  python3 -m factorymind.sim.a.mcp_server --http --port 8765
```

For MuJoCo on a machine with MuJoCo installed:

```bash
FACTORYMIND_SIM_BACKEND=mujoco FACTORYMIND_SIM_AUTO_FRAME=1 \
  python3 -m factorymind.sim.a.mcp_server --http --port 8765
```

### 3. Telemetry + Frame Server

```bash
cd /Users/emanschool/dell-nvidia-hackathon/factorymind
PYTHONDONTWRITEBYTECODE=1 python3 -m factorymind.sim.a.serve_team_feed --port 8766
```

### 4. Dashboard

```bash
cd /Users/emanschool/dell-nvidia-hackathon/factorymind/factorymind/demo/dashboard
npm run dev -- --host 127.0.0.1 --port 3000
```

Open:

```text
http://localhost:3000/
```

### 5. Dashboard Build Check

```bash
cd /Users/emanschool/dell-nvidia-hackathon/factorymind/factorymind/demo/dashboard
npm run build
```

---

## Demo Script

### Recommended Local Demo

1. Start the command bridge on `:8765`.
2. Start the telemetry server on `:8766`.
3. Start the dashboard on `:3000`.
4. Open `http://localhost:3000/`.
5. Show the FactoryMind control room.
6. Pick a scenario:
   - `Default`
   - `Sort Green`
   - `Misaligned`
   - `Conveyor`
   - `Empty Bin`
7. Type an operator command:

```text
Run five safe assembly steps
```

8. Show that the backend advances the cell and the dashboard updates.

### What To Say

FactoryMind is a local factory-cell agent demo. The operator gives natural-language instructions, the local backend turns them into safe structured actions, the simulation advances step by step, and the dashboard shows live telemetry and cell state. The same architecture can be connected to local GB10 model endpoints for DiffusionGemma and Gemma AR.

### What Not To Oversell

- On a laptop without MuJoCo, this is the mock backend, not full physics.
- The current stable demo uses the deterministic oracle for safe behavior.
- DiffusionGemma/Gemma model serving is the intended GB10 integration path, not required for the local mock demo.

---

## GB10 / Full Stack Intent

The intended event hardware is the Dell Pro Max with GB10.

Model story:

- DiffusionGemma is the hero path.
- Gemma AR is the baseline/fallback path.
- Both should be served locally.
- The model should emit structured `CellPlan` blocks.
- The sim should validate every action before stepping.

Original model endpoints:

```text
DiffusionGemma: http://localhost:8000/v1
Gemma AR:       http://localhost:8001/v1
```

GB10 target terminal layout:

```text
Terminal 1 — model server
Terminal 2 — sim MCP/HTTP server (:8765)
Terminal 3 — telemetry/frame server (:8766)
Terminal 4 — dashboard (:3000 or :5173)
Terminal 5 — NemoClaw sandbox if needed
```

NemoClaw remains the on-brief harness target. The local dashboard path is browser-friendly and can run without NemoClaw for demos, testing, and fallback.

---

## Project Status

### Green

- Mock sim imports and runs without MuJoCo.
- Scenario smoke tests pass in mock mode.
- Normal smoke test cleanly skips MuJoCo if not installed.
- Dashboard builds with `npm run build`.
- Dashboard runs locally on port `3000`.
- Command bridge responds to `/command`.
- Telemetry server serves `run.jsonl`.
- GitHub `main` has been pushed and synced multiple times.
- Dashboard received a modern organic/natural visual redesign.

### Partially Green

- MuJoCo backend exists but needs `mujoco` installed locally to validate.
- Live MuJoCo frames/stream are supported in the frontend, but laptop mock mode does not produce true MuJoCo visuals.
- DiffusionGemma/Gemma serving is designed but depends on GB10 setup.

### Next Work

- Install and validate MuJoCo locally or on GB10.
- Run `FACTORYMIND_SIM_BACKEND=mujoco` smoke tests.
- Validate `/sim/stream.mjpg` with real frames.
- Connect local model endpoint to the planning loop.
- Record and replay real DiffusionGemma vs Gemma AR telemetry.
- Polish final talk track and screenshots.
- Decide whether generated replay PNGs should remain tracked or be treated as runtime artifacts.

---

## Repository Map

```text
.
├── overview.md                                      # this file
├── how-to-run.md                                    # terminal-by-terminal runbook
├── factorymind/
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── factorymind/
│       ├── sim/
│       │   └── a/
│       │       ├── cell.py
│       │       ├── mujoco_cell.py
│       │       ├── oracle.py
│       │       ├── mcp_server.py
│       │       ├── run_team_feed.py
│       │       ├── serve_team_feed.py
│       │       ├── smoke_test.py
│       │       └── assets/
│       ├── agent/
│       │   ├── loop.py
│       │   ├── client.py
│       │   └── schemas.py
│       └── demo/
│           └── dashboard/
│               ├── package.json
│               ├── src/
│               │   ├── App.tsx
│               │   ├── index.css
│               │   ├── components/
│               │   └── hooks/
│               └── tailwind.config.js
└── scripts/
```

---

## Glossary

- **FactoryMind:** the project and local control-room agent concept.
- **CellPlan:** structured action block for one control step.
- **C2 state:** structured sim state describing robots, parts, stations, events, task, and scenario.
- **Oracle:** deterministic safe planner used for stable demos and tests.
- **Mock backend:** Python-only sim path that needs no MuJoCo or GPU.
- **MuJoCo backend:** physics/rendering sim path.
- **Telemetry JSONL:** line-delimited decision/event data consumed by the dashboard.
- **GB10:** Dell/NVIDIA local AI target hardware.

---

## One-Line Pitch

FactoryMind is a local GB10 factory-cell control room: natural-language commands become validated robot actions, the simulation advances safely, and live telemetry proves the local-agent loop without sending factory data to the cloud.
