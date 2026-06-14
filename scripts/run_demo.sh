#!/usr/bin/env bash
# FactoryMind Full Demo Runner
# Assumes box_setup.sh has already run. Orchestrates the full demo sequence.
#
# Usage:
#   cd ~/factorymind
#   bash scripts/run_demo.sh [--ar-only] [--replay]
#
# --ar-only   Skip DiffusionGemma; demo with AR Gemma4 + architecture story
# --replay    Skip live models; replay a recorded telemetry JSONL (worst-case demo)

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()     { echo -e "${GREEN}[OK]${NC} $*"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()   { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }
section(){ echo -e "\n${BLUE}══════════════════════════════════════${NC}"; echo -e "${BLUE}  $*${NC}"; echo -e "${BLUE}══════════════════════════════════════${NC}"; }

MODE="${1:-full}"
TELEMETRY_DIR="telemetry"
mkdir -p "$TELEMETRY_DIR"

# Cleanup handler
PIDS=()
cleanup() {
  echo ""
  warn "Shutting down..."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  ok "All processes stopped."
}
trap cleanup EXIT INT TERM

# ── Demo fallback ladder ────────────────────────────────────────────────────────
# Tier 1 (best):  DiffusionGemma + AR side-by-side latency race
# Tier 2 (good):  AR Gemma4 only + sim + latency architecture
# Tier 3 (worst): Sim + oracle/replay of recorded outputs

detect_tier() {
  DIFFUSION_UP=false; AR_UP=false
  curl -sf http://localhost:8000/v1/models > /dev/null 2>&1 && DIFFUSION_UP=true
  curl -sf http://localhost:8001/v1/models > /dev/null 2>&1 && AR_UP=true

  if [[ "$DIFFUSION_UP" == "true" && "$AR_UP" == "true" && "$MODE" != "--ar-only" && "$MODE" != "--replay" ]]; then
    echo "1"
  elif [[ "$AR_UP" == "true" && "$MODE" != "--replay" ]]; then
    echo "2"
  else
    echo "3"
  fi
}

# ── Step 0: Hardware check ──────────────────────────────────────────────────────
section "0. Pre-flight"
[[ "$(uname -m)" == "aarch64" ]] && ok "aarch64 confirmed" || warn "Not aarch64 — running in dev mode"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null \
  && ok "GPU detected" || warn "GPU not visible"

TIER=$(detect_tier)
case "$TIER" in
  1) ok  "Demo tier: BEST — DiffusionGemma + AR side-by-side race" ;;
  2) warn "Demo tier: GOOD — AR Gemma4 only (diffusion not ready or skipped)" ;;
  3) warn "Demo tier: WORST — Replay mode (no live model)" ;;
esac

# ── Step 1: Smoke test ──────────────────────────────────────────────────────────
section "1. Sim smoke test"
python3 -m factorymind.sim.a.smoke_test \
  && ok "Oracle smoke test passed" \
  || fail "Smoke test failed — check Python install"

# ── Step 2: MCP server ──────────────────────────────────────────────────────────
section "2. MCP server (HTTP)"
MCP_PORT="${MCP_PORT:-8765}"
python3 -m factorymind.sim.a.mcp_server --http --port "${MCP_PORT}" &
PIDS+=($!)
sleep 2
curl -sf "http://localhost:${MCP_PORT}/mcp" > /dev/null 2>&1 \
  && ok "MCP server ready on :${MCP_PORT}" \
  || warn "MCP server slow to start — continuing anyway"

# ── Step 3: Run based on tier ──────────────────────────────────────────────────
case "$TIER" in

  1)
    section "3. Tier 1 — Live diffusion vs AR race"
    echo "  Enabling dual_model_race in NemoClaw config..."
    # Patch nemoclaw.yaml to enable dual race (sed is safe here, scripted value)
    sed -i 's/dual_model_race: false/dual_model_race: true/' \
      factorymind/factorymind/agent/nemoclaw.yaml 2>/dev/null || true

    echo "  Starting OpenClaw agent via NemoClaw..."
    bash scripts/start_openclaw.sh &
    PIDS+=($!)
    ;;

  2)
    section "3. Tier 2 — AR Gemma4 live demo"
    echo "  Pitch: 'Same always-on local controller; diffusion path ready, AR running today.'"
    bash scripts/start_openclaw.sh &
    PIDS+=($!)
    ;;

  3)
    section "3. Tier 3 — Replay mode (worst-case demo)"
    REPLAY_FILE="${TELEMETRY_DIR}/run.jsonl"
    if [[ -f "$REPLAY_FILE" ]]; then
      ok "Replay file found: $REPLAY_FILE"
      echo "  Pitch: 'Control loop and schema proven; model endpoints pending first boot.'"
      echo "  Streaming replay... (Role C dashboard reads this file)"
      cat "$REPLAY_FILE"
    else
      warn "No replay file at $REPLAY_FILE — running oracle loop to generate one"
      python3 -m factorymind.agent.loop --mode mock --verbose 2>&1 | tee "$REPLAY_FILE"
      ok "Oracle replay saved to $REPLAY_FILE"
    fi
    ;;

esac

# ── Step 4: Wait ───────────────────────────────────────────────────────────────
section "Demo running"
echo "  MCP server:  http://localhost:${MCP_PORT}/mcp"
echo "  Telemetry:   ${TELEMETRY_DIR}/run.jsonl  (Role C reads this)"
echo ""
echo "  Press Ctrl+C to stop."
wait
