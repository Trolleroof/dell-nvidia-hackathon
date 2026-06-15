"""Serve telemetry + sim frames + live dashboard (stdlib only).

    python -m factorymind.sim.a.serve_team_feed
    python -m factorymind.sim.a.serve_team_feed --port 8766

Dashboard:
    http://localhost:8766/              ← live operator dashboard (open this)

Feed URLs (consumed by the dashboard JS):
    http://localhost:8766/sim/latest.png
    http://localhost:8766/telemetry/run.jsonl
    http://localhost:8766/telemetry/diffusion_run.jsonl
    http://localhost:8766/telemetry/ar_run.jsonl

MCP server must be running on :8765 for the Run button to work:
    python -m factorymind.sim.a.mcp_server --http --port 8765
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from factorymind.sim.a.frame_export import latest_frame_path
from factorymind.sim.a.telemetry_bridge import default_telemetry_path, telemetry_dir

# ── Dashboard HTML ─────────────────────────────────────────────────────────────
# Self-contained: no build step, no CDN, no external deps.
# Polls /sim/latest.png (same origin) for the MuJoCo render.
# POSTs to :8765/command (MCP server REST bridge) to send instructions.
# Polls /telemetry/run.jsonl for the event log.
_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FactoryMind — Cell Monitor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0d0d;color:#e0e0e0;font-family:'Courier New',monospace;display:flex;flex-direction:column;height:100vh;overflow:hidden}
header{background:#111;border-bottom:1px solid #1e1e1e;padding:10px 20px;display:flex;align-items:center;gap:12px;flex-shrink:0}
h1{font-size:17px;font-weight:bold;color:#00d4ff;letter-spacing:3px}
.badge{border:1px solid #333;border-radius:3px;padding:2px 8px;font-size:11px;color:#666}
.badge.live{border-color:#00ff88;color:#00ff88}
.badge.done{border-color:#ffd700;color:#ffd700}
main{flex:1;display:flex;overflow:hidden}
.cam{flex:2;padding:14px;display:flex;flex-direction:column;gap:8px;min-width:0}
#frame{width:100%;border:1px solid #1e1e1e;border-radius:4px;background:#0a0a0a;display:block}
.cam-sub{font-size:11px;color:#444}
.ctrl{flex:1;min-width:260px;max-width:340px;padding:14px;border-left:1px solid #1a1a1a;display:flex;flex-direction:column;gap:14px;overflow-y:auto}
.lbl{font-size:10px;letter-spacing:1px;color:#555;text-transform:uppercase;margin-bottom:5px}
.task-box{background:#111;border:1px solid #222;border-radius:3px;padding:9px;font-size:12px;color:#00d4ff;word-break:break-word}
input[type=text]{width:100%;background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:7px 9px;color:#e0e0e0;font:inherit;font-size:12px;outline:none}
input[type=text]:focus{border-color:#00d4ff}
.row{display:flex;gap:8px;align-items:center}
button{background:#00d4ff;color:#000;border:none;border-radius:3px;padding:7px 14px;font:inherit;font-size:12px;font-weight:bold;cursor:pointer;white-space:nowrap}
button:hover{background:#00b8d9}
button:disabled{background:#222;color:#555;cursor:not-allowed}
input[type=number]{width:62px;background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:7px 6px;color:#e0e0e0;font:inherit;font-size:12px;outline:none;text-align:center}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.stat{background:#111;border:1px solid #1a1a1a;border-radius:3px;padding:7px}
.stat .k{font-size:10px;color:#444}
.stat .v{font-size:12px;color:#ccc;margin-top:3px;word-break:break-all}
.log{background:#080808;border:1px solid #1a1a1a;border-radius:3px;padding:8px;font-size:11px;line-height:1.7;overflow-y:auto;flex:1;min-height:80px}
.ev{color:#555}
.ev.ok{color:#00ff88}
.ev.done{color:#ffd700;font-weight:bold}
.ev.err{color:#ff4455}
.ev.warn{color:#ff8800}
.ev.info{color:#888}
</style>
</head>
<body>
<header>
  <h1>FACTORYMIND</h1>
  <span class="badge">MuJoCo Cell</span>
  <span class="badge live" id="live-badge">● LIVE</span>
  <span class="badge" id="step-badge">step —</span>
  <span class="badge" id="done-badge" style="display:none">✓ DONE</span>
</header>
<main>
  <div class="cam">
    <img id="frame" src="/sim/latest.png" alt="Cell render" onerror="this.style.opacity=0.3">
    <div class="cam-sub">MuJoCo render — refreshes every second · served from frames/latest.png</div>
  </div>
  <div class="ctrl">

    <div>
      <div class="lbl">Current Task</div>
      <div class="task-box" id="task-display">—</div>
    </div>

    <div>
      <div class="lbl">Send Instruction</div>
      <input id="instruction" type="text"
             placeholder="Move all parts from bin_a to station_1.">
    </div>

    <div>
      <div class="row">
        <button id="run-btn" onclick="sendCommand()">▶ Run</button>
        <input id="steps" type="number" value="10" min="1" max="50" title="Steps">
        <span style="font-size:11px;color:#555">steps</span>
      </div>
      <div id="cmd-status" style="font-size:11px;color:#555;margin-top:6px"></div>
    </div>

    <div>
      <div class="lbl">Robot State</div>
      <div class="grid">
        <div class="stat"><div class="k">Robot 0</div><div class="v" id="r0">—</div></div>
        <div class="stat"><div class="k">Robot 1</div><div class="v" id="r1">—</div></div>
        <div class="stat"><div class="k">Parts</div><div class="v" id="parts">—</div></div>
        <div class="stat"><div class="k">Stations</div><div class="v" id="stations">—</div></div>
      </div>
    </div>

    <div style="flex:1;display:flex;flex-direction:column;min-height:0">
      <div class="lbl">Event Log <span id="log-count" style="color:#444"></span></div>
      <div class="log" id="event-log"><div class="ev info">waiting for sim events…</div></div>
    </div>

  </div>
</main>
<script>
const MCP = 'http://localhost:8765';
let lastLineCount = 0;

// ── Image polling ──────────────────────────────────────────────────────────────
function refreshFrame(){
  const img = document.getElementById('frame');
  const prev = img.src;
  const next = '/sim/latest.png?' + Date.now();
  const tmp = new Image();
  tmp.onload = () => { img.src = next; };
  tmp.onerror = () => {};
  tmp.src = next;
}
setInterval(refreshFrame, 1000);

// ── Robot state polling ────────────────────────────────────────────────────────
async function pollState(){
  try {
    const r = await fetch(MCP + '/sim/state', {cache:'no-store'});
    if (!r.ok) return;
    const s = await r.json();

    document.getElementById('step-badge').textContent = 'step ' + (s.step ?? '—');
    document.getElementById('task-display').textContent = s.task || '—';

    const doneBadge = document.getElementById('done-badge');
    if (s.done){ doneBadge.style.display=''; } else { doneBadge.style.display='none'; }

    if (s.robots && s.robots[0]){
      const fmt = rob => rob.gripper + (rob.holding ? ' / ' + rob.holding : '');
      document.getElementById('r0').textContent = fmt(s.robots[0]);
      if (s.robots[1]) document.getElementById('r1').textContent = fmt(s.robots[1]);
    }
    if (s.parts)
      document.getElementById('parts').textContent =
        s.parts.map(p => p.id.replace('part_','p') + '@' + (p.at||'?')).join(' ');
    if (s.stations)
      document.getElementById('stations').textContent =
        s.stations.map(st => st.id.replace('station_','s') + ':' + st.status).join(' ');
  } catch {}
}
setInterval(pollState, 1200);
pollState();

// ── Telemetry polling ──────────────────────────────────────────────────────────
const EV_CLASS = {
  task_complete:'done', pick_success:'ok', place_success:'ok',
  collision:'err', grip_miss:'warn', release_empty:'warn',
  invalid_target:'warn', gripper_busy:'warn',
};
async function pollTelemetry(){
  try {
    const r = await fetch('/telemetry/run.jsonl?' + Date.now(), {cache:'no-store'});
    if (!r.ok) return;
    const text = await r.text();
    const lines = text.trim().split('\\n').filter(Boolean);
    if (lines.length === lastLineCount) return;
    lastLineCount = lines.length;
    document.getElementById('log-count').textContent = '(' + lines.length + ')';
    const log = document.getElementById('event-log');
    log.innerHTML = lines.slice(-30).reverse().map(line => {
      try {
        const row = JSON.parse(line);
        const ev = row.sim_event || 'task_progress';
        const cls = EV_CLASS[ev] || 'info';
        return '<div class="ev ' + cls + '">'
          + 's' + String(row.step).padStart(2,'0')
          + ' ' + (row.action_summary || '').slice(0,40)
          + ' → <b>' + ev + '</b></div>';
      } catch { return ''; }
    }).join('');
  } catch {}
}
setInterval(pollTelemetry, 1000);
pollTelemetry();

// ── Send instruction ───────────────────────────────────────────────────────────
async function sendCommand(){
  const btn = document.getElementById('run-btn');
  const status = document.getElementById('cmd-status');
  const instruction = document.getElementById('instruction').value.trim();
  const steps = Math.max(1, Math.min(50, parseInt(document.getElementById('steps').value)||10));

  btn.disabled = true;
  btn.textContent = '⏳ Running…';
  status.textContent = 'Oracle running ' + steps + ' steps…';
  lastLineCount = 0;

  try {
    const r = await fetch(MCP + '/command', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({instruction, steps}),
    });
    const data = await r.json();
    status.textContent = data.done
      ? '✓ Task complete in ' + data.steps_run + ' steps'
      : 'Ran ' + data.steps_run + ' steps' + (data.did_reset ? ' (auto-reset)' : '');
    pollState();
    pollTelemetry();
    refreshFrame();
  } catch(e){
    status.textContent = '✗ Error: ' + e.message + ' — is the MCP server running on :8765?';
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ Run';
  }
}

document.getElementById('instruction').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendCommand();
});
</script>
</body>
</html>
"""


class FeedHandler(SimpleHTTPRequestHandler):
    telemetry_root: Path = telemetry_dir()
    frames_root: Path = latest_frame_path().parent

    def do_GET(self) -> None:
        clean = self.path.split("?", 1)[0]
        if clean in ("/", "/dashboard"):
            body = _DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0]
        if clean.startswith("/telemetry/"):
            rel = clean.removeprefix("/telemetry/").lstrip("/")
            return str((self.telemetry_root / rel).resolve())
        if clean.startswith("/sim/"):
            rel = clean.removeprefix("/sim/").lstrip("/")
            return str((self.frames_root / rel).resolve())
        return str((self.telemetry_root / "run.jsonl").resolve())

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print(f"[serve] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve live dashboard + telemetry + sim frames")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    telemetry_dir().mkdir(parents=True, exist_ok=True)
    latest_frame_path().parent.mkdir(parents=True, exist_ok=True)

    handler = partial(FeedHandler, directory=str(telemetry_dir()))
    server = ThreadingHTTPServer((args.host, args.port), handler)

    display_host = "localhost" if args.host in ("0.0.0.0", "") else args.host
    print("=" * 54)
    print("  FactoryMind Dashboard")
    print("=" * 54)
    print(f"\n  >>> Open in browser:  http://{display_host}:{args.port}/\n")
    print(f"  MuJoCo frame:  http://{display_host}:{args.port}/sim/latest.png")
    print(f"  Telemetry:     http://{display_host}:{args.port}/telemetry/run.jsonl")
    print(f"\n  MCP server must be on :8765 for the Run button:")
    print(f"    python -m factorymind.sim.a.mcp_server --http --port 8765")
    if not default_telemetry_path().is_file():
        print("\n  WARN: telemetry/run.jsonl missing — start MCP server and send a command first")
    print("\n  Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] stopped")


if __name__ == "__main__":
    main()
