#!/usr/bin/env bash
# Start the FactoryMind OpenClaw agent via NemoClaw + OpenShell.
# Falls back to bare OpenClaw if NemoClaw is not installed.
#
# Usage:
#   cd ~/factorymind
#   bash scripts/start_openclaw.sh
#   bash scripts/start_openclaw.sh --http-mcp   # MCP over HTTP instead of stdio

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

AGENT_DIR="factorymind/factorymind/agent"
MCP_PORT="${MCP_PORT:-8765}"
MCP_HTTP="${1:-}"
TELEMETRY_DIR="telemetry"

mkdir -p "$TELEMETRY_DIR"

# ── 1. Pre-flight: verify at least one model endpoint is up ────────────────────
echo ""
echo "=== 1. Endpoint pre-flight ==="
AR_UP=false
DIFFUSION_UP=false

curl -sf http://localhost:8001/v1/models > /dev/null 2>&1  && { ok "AR Gemma4   :8001 ready"; AR_UP=true; }    || warn "AR Gemma4   :8001 not reachable — run start_models.sh first"
curl -sf http://localhost:8000/v1/models > /dev/null 2>&1  && { ok "Diffusion   :8000 ready"; DIFFUSION_UP=true; } || warn "Diffusion   :8000 not ready — will use AR fallback"

[[ "$AR_UP" == "true" || "$DIFFUSION_UP" == "true" ]] \
  || fail "No model endpoint is reachable. Run scripts/start_models.sh first."

# ── 2. MCP server ──────────────────────────────────────────────────────────────
echo ""
echo "=== 2. MCP server ==="
MCP_PID=""

if [[ "$MCP_HTTP" == "--http-mcp" ]]; then
  echo "Starting MCP in HTTP mode on :${MCP_PORT}..."
  python3 -m factorymind.sim.a.mcp_server --http --port "${MCP_PORT}" &
  MCP_PID=$!
  sleep 2
  curl -sf "http://localhost:${MCP_PORT}/mcp" > /dev/null 2>&1 \
    && ok "MCP HTTP server ready on :${MCP_PORT}" \
    || warn "MCP HTTP server may still be starting"

  # Update openclaw.json to use HTTP transport for this session
  MCP_TRANSPORT="streamable-http"
  MCP_URL="http://localhost:${MCP_PORT}/mcp"
else
  echo "MCP will run in stdio mode (OpenClaw/NemoClaw starts it via the config)."
  MCP_TRANSPORT="stdio"
  MCP_URL=""
fi

# ── 3. Choose runtime: NemoClaw → OpenClaw fallback ───────────────────────────
echo ""
echo "=== 3. Starting agent runtime ==="

cleanup() {
  [[ -n "$MCP_PID" ]] && kill "$MCP_PID" 2>/dev/null || true
  echo ""
  ok "Shutdown complete."
}
trap cleanup EXIT INT TERM

if command -v nemoclaw &>/dev/null; then
  ok "NemoClaw found — starting with OpenShell sandbox"
  echo "  Config:  ${AGENT_DIR}/nemoclaw.yaml"
  echo "  Policy:  ${AGENT_DIR}/openshell-policy.yaml"
  echo "  Agent:   ${AGENT_DIR}/openclaw.json"
  echo ""
  nemoclaw start \
    --config  "${AGENT_DIR}/nemoclaw.yaml" \
    --policy  "${AGENT_DIR}/openshell-policy.yaml" \
    --agent   "${AGENT_DIR}/openclaw.json"

elif command -v openclaw &>/dev/null; then
  warn "NemoClaw not found — running bare OpenClaw (no OpenShell sandbox)"
  warn "Security policies will NOT be enforced. Use only for dev/testing."
  echo "  Config:  ${AGENT_DIR}/openclaw.json"
  echo ""
  openclaw \
    --config "${AGENT_DIR}/openclaw.json"

else
  fail "Neither 'nemoclaw' nor 'openclaw' found.
  Run:  bash scripts/box_setup.sh
  Then: bash scripts/start_openclaw.sh"
fi
