
  Terminal 1 — DiffusionGemma (:8000)
  /home/dell/factorymind/.venv/bin/python /home/dell/factorymind/serve_diffusiongemma.py --host 0.0.0.0 --port 8000

  Terminal 2 — MCP sim server (:8765)
  cd /home/dell/Desktop/dell-nvidia-hackathon/factorymind
  FACTORYMIND_SIM_BACKEND=mujoco FACTORYMIND_SIM_AUTO_FRAME=1 \
    /home/dell/Desktop/dell-nvidia-hackathon/.venv/bin/python -m factorymind.sim.a.mcp_server --http --port 8765

  Terminal 3 — Telemetry + frame feed (:8766)
  cd /home/dell/Desktop/dell-nvidia-hackathon/factorymind
  /home/dell/Desktop/dell-nvidia-hackathon/.venv/bin/python -m factorymind.sim.a.serve_team_feed --port 8766

  Terminal 4 — Dashboard (:5173)
  cd /home/dell/Desktop/dell-nvidia-hackathon/factorymind/factorymind/demo/dashboard
  npm run dev

  Terminal 5 — NemoClaw sandbox (only if :18789 is down, e.g. after reboot)
  sg docker -c "nemoclaw onboard --resume --name factorymind --non-interactive --yes"

  Then open http://localhost:5173/#/agent and queue a command.
