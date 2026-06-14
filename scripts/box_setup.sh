#!/usr/bin/env bash
# GB10 First-Hour Setup — FactoryMind
# Run once after first SSH into the Dell Pro Max with GB10.
# Assumes: repo + models already on ~/factorymind/ (from SSD rsync).
#
# Usage:
#   cd ~/factorymind
#   bash scripts/box_setup.sh

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

echo "=============================================="
echo "  FactoryMind — GB10 Box Setup"
echo "=============================================="
date

# ── 0. Hardware checks ─────────────────────────────────────────────────────────
echo ""
echo "=== 0. Hardware ==="
ARCH=$(uname -m)
[[ "$ARCH" == "aarch64" ]] || fail "Expected aarch64, got $ARCH. Is this the GB10?"
ok "Architecture: $ARCH"

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null \
  && ok "GPU detected" \
  || warn "nvidia-smi failed — GPU may not be visible yet"

# ── 1. System packages ─────────────────────────────────────────────────────────
echo ""
echo "=== 1. System packages ==="
sudo apt-get update -qq
sudo apt-get install -y \
  python3-pip python3-venv python3-dev \
  nodejs npm \
  curl git wget \
  build-essential \
  libgl1 libglfw3-dev libgles2          # headless GL for MuJoCo
ok "System packages installed"

# ── 2. Python dependencies ─────────────────────────────────────────────────────
echo ""
echo "=== 2. Python dependencies ==="
# DO NOT copy Mac wheels — install fresh on aarch64
cd ~/factorymind
pip3 install --upgrade pip -q
pip3 install -r factorymind/requirements.txt -q
pip3 install -e factorymind/ -q

# MuJoCo — aarch64 wheel is on PyPI
pip3 install "mujoco>=3.1,<4" numpy -q \
  && ok "MuJoCo installed" \
  || warn "MuJoCo install failed — sim will fall back to mock backend"
ok "Python dependencies ready"

# ── 3. OpenClaw ────────────────────────────────────────────────────────────────
echo ""
echo "=== 3. OpenClaw ==="
if command -v openclaw &>/dev/null; then
  ok "OpenClaw already installed: $(openclaw --version 2>/dev/null || echo 'version unknown')"
else
  echo "Installing OpenClaw via npm..."
  npm install -g openclaw 2>/dev/null && ok "OpenClaw installed via npm" || {
    echo "npm install failed, trying curl installer..."
    curl -fsSL https://raw.githubusercontent.com/openclaw/openclaw/main/install.sh | bash \
      && ok "OpenClaw installed via curl" \
      || warn "OpenClaw install failed — run manually: npm install -g openclaw"
  }
fi

# ── 4. NemoClaw + OpenShell ────────────────────────────────────────────────────
echo ""
echo "=== 4. NemoClaw + OpenShell (NVIDIA bundle) ==="
if command -v nemoclaw &>/dev/null; then
  ok "NemoClaw already installed: $(nemoclaw --version 2>/dev/null || echo 'version unknown')"
else
  echo "Installing NemoClaw (this installs OpenShell automatically)..."
  bash <(curl -fsSL https://raw.githubusercontent.com/NVIDIA/nemoclaw/main/install.sh) \
    && ok "NemoClaw + OpenShell installed" \
    || warn "NemoClaw install failed. Try: https://www.nvidia.com/en-us/ai/nemoclaw/
       Fallback: openclaw will run without OpenShell sandbox (start_openclaw.sh handles this)"
fi

# ── 5. Docker + NVIDIA Container Toolkit ──────────────────────────────────────
echo ""
echo "=== 5. Docker + NVIDIA Container Toolkit ==="
if command -v docker &>/dev/null; then
  ok "Docker: $(docker --version)"
else
  warn "Docker not found — install from https://docs.docker.com/engine/install/ubuntu/"
fi

if docker info 2>/dev/null | grep -q "nvidia"; then
  ok "NVIDIA Container Toolkit active"
else
  warn "NVIDIA Container Toolkit may not be configured. Check: docker run --gpus all nvidia/cuda:12.0-base nvidia-smi"
fi

# ── 6. Telemetry directory ─────────────────────────────────────────────────────
echo ""
echo "=== 6. Directories ==="
mkdir -p ~/factorymind/telemetry
ok "telemetry/ ready"

# ── 7. Smoke test ──────────────────────────────────────────────────────────────
echo ""
echo "=== 7. Smoke test (mock sim, no GPU required) ==="
cd ~/factorymind
python3 -m factorymind.sim.a.smoke_test \
  && ok "Smoke test passed" \
  || warn "Smoke test failed — check Python deps above"

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  Setup summary"
echo "=============================================="
command -v openclaw  &>/dev/null && ok "openclaw"  || warn "openclaw  — NOT installed"
command -v nemoclaw  &>/dev/null && ok "nemoclaw"  || warn "nemoclaw  — NOT installed (will run bare openclaw)"
command -v docker    &>/dev/null && ok "docker"    || warn "docker    — NOT installed (model serving will fail)"
echo ""
echo "Next steps:"
echo "  1. bash scripts/start_models.sh           # serve DiffusionGemma + AR Gemma4"
echo "  2. bash scripts/start_openclaw.sh         # start the agent"
echo "  3. bash scripts/run_demo.sh               # full demo"
echo ""
ok "Box setup complete — $(date)"
