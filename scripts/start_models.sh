#!/usr/bin/env bash
# Start model serving on the GB10.
# AR Gemma4 (:8001) goes first — unblocks the team immediately.
# DiffusionGemma (:8000) is the hero path — comes second.
#
# Usage:
#   MODEL_DIR=~/factorymind/models bash scripts/start_models.sh
#   bash scripts/start_models.sh --ar-only         # safe demo mode
#   bash scripts/start_models.sh --diffusion-only  # debug diffusion separately
#
# Prerequisites: Docker + NVIDIA Container Toolkit + model weights on MODEL_DIR

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

MODEL_DIR="${MODEL_DIR:-$HOME/factorymind/models}"
DIFFUSION_MODEL_DIR="${MODEL_DIR}/diffusiongemma"
AR_MODEL_DIR="${MODEL_DIR}/gemma4-ar"
DIFFUSION_URL="http://localhost:8000/v1"
AR_URL="http://localhost:8001/v1"
VLLM_IMAGE="vllm/vllm-openai:gemma4"

wait_for_endpoint() {
  local url="$1" label="$2" timeout=120 elapsed=0
  echo -n "  Waiting for $label"
  until curl -sf "${url}/models" > /dev/null 2>&1; do
    sleep 3; elapsed=$((elapsed+3))
    echo -n "."
    [[ $elapsed -ge $timeout ]] && { echo ""; warn "$label not ready after ${timeout}s"; return 1; }
  done
  echo ""
  ok "$label ready at $url"
}

start_ar() {
  echo ""
  echo "=== AR Gemma4 → :8001 (baseline — start this first) ==="

  [[ -d "$AR_MODEL_DIR" ]] || fail "AR model not found at $AR_MODEL_DIR. Copy weights from SSD first."

  docker stop gemma4-ar 2>/dev/null || true
  docker rm   gemma4-ar 2>/dev/null || true

  docker run -d \
    --name gemma4-ar \
    --gpus all \
    --runtime=nvidia \
    -p 8001:8000 \
    -v "${AR_MODEL_DIR}:/model:ro" \
    "${VLLM_IMAGE}" \
      --model /model \
      --trust-remote-code \
      --enable-auto-tool-choice \
      --tool-call-parser gemma4 \
      --reasoning-parser gemma4 \
      --max-model-len 4096 \
      --gpu-memory-utilization 0.45
  ok "AR container started"
  wait_for_endpoint "$AR_URL" "AR Gemma4"
}

start_diffusion() {
  echo ""
  echo "=== DiffusionGemma → :8000 (hero path) ==="
  echo "  HARD STOP: if not ready by 12:00, run start_models.sh --ar-only and demo AR path."

  [[ -d "$DIFFUSION_MODEL_DIR" ]] || fail "Diffusion model not found at $DIFFUSION_MODEL_DIR."

  docker stop diffusiongemma 2>/dev/null || true
  docker rm   diffusiongemma 2>/dev/null || true

  docker run -d \
    --name diffusiongemma \
    --gpus all \
    --runtime=nvidia \
    -p 8000:8000 \
    -e VLLM_USE_V2_MODEL_RUNNER=1 \
    -v "${DIFFUSION_MODEL_DIR}:/model:ro" \
    "${VLLM_IMAGE}" \
      --model /model \
      --trust-remote-code \
      --attention-backend TRITON_ATTN \
      --enable-auto-tool-choice \
      --tool-call-parser gemma4 \
      --reasoning-parser gemma4 \
      --hf-overrides '{"diffusion_sampler":"entropy_bound","diffusion_entropy_bound":0.1}' \
      --diffusion-config '{"canvas_length":256}' \
      --enable-chunked-prefill \
      --max-model-len 4096 \
      --gpu-memory-utilization 0.45
  ok "DiffusionGemma container started"
  wait_for_endpoint "$DIFFUSION_URL" "DiffusionGemma"
}

write_c4() {
  # Write the C4 endpoint contract for Role B
  local out="factorymind/factorymind/agent/c4_endpoints.json"
  cat > "$out" << EOF
{
  "diffusion": {
    "base_url": "${DIFFUSION_URL}",
    "model": "nvidia/diffusiongemma-26B-A4B-it-NVFP4",
    "structured_output": true,
    "tool_call_parser": "gemma4",
    "max_model_len": 4096
  },
  "ar": {
    "base_url": "${AR_URL}",
    "model": "google/gemma-4-26B-A4B-it",
    "structured_output": true,
    "tool_call_parser": "gemma4",
    "max_model_len": 4096
  }
}
EOF
  ok "C4 endpoints written → $out"
}

# ── Main ───────────────────────────────────────────────────────────────────────
MODE="${1:-both}"

case "$MODE" in
  --ar-only)
    start_ar
    ;;
  --diffusion-only)
    start_diffusion
    ;;
  both|*)
    start_ar
    start_diffusion
    ;;
esac

write_c4

echo ""
echo "Running containers:"
docker ps --filter "name=gemma4-ar" --filter "name=diffusiongemma" \
  --format "  {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Next: bash scripts/start_openclaw.sh"
