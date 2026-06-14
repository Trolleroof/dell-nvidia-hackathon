"""Role C — Frontend: the diffusion-vs-AR latency dashboard.

This package ships two builds of the same dashboard:

* ``static/index.html`` — a single self-contained file with ZERO dependencies
  (no CDN, no charting lib). The robust fallback that serves on an unfamiliar
  aarch64 / DGX OS box with no outbound internet.
* ``dashboard/`` — a React + TypeScript + Vite + Tailwind build for the polished
  version (charts via a tiny inline SVG renderer; no external runtime CDN).

``gen_mock_telemetry.py`` emits the frozen C5 telemetry schema so both builds can
be rehearsed (Mock / Replay / Live) with no GPU.
"""
