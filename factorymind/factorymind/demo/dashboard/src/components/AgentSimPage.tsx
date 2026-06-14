import { useEffect, useRef, useState } from "react";
import { CellView } from "./CellView";
import { ActionStream } from "./ActionStream";
import { LatencyRace } from "./LatencyRace";
import { StatsPanel } from "./StatsPanel";
import type { Mode, TelemetryRow, Aggregate } from "../types";

interface ChatMessage {
  role: "operator" | "agent";
  text: string;
  at: string;
}

interface Props {
  mode: Mode;
  setMode: (mode: Mode) => void;
  playing: boolean;
  setPlaying: (playing: boolean) => void;
  speed: number;
  setSpeed: (speed: number) => void;
  cloud: boolean;
  setCloud: (cloud: boolean) => void;
  liveUrl: string;
  setLiveUrl: (url: string) => void;
  latest: { d?: TelemetryRow; a?: TelemetryRow };
  stream: TelemetryRow[];
  step: number;
  hint: string;
  cloudRtt: number;
  aggregates: { d: Aggregate | null; a: Aggregate | null };
  decisions: number;
  resetKey: number;
  onReset: () => void;
  onFetchIsolatedReplay: () => void;
}

const quickCommands = [
  "Run five safe assembly steps",
  "Pause on collision or parse failure",
  "Explain the last action",
  "Switch to live feed when ready",
];

const LIVE_FEED_URL = "http://localhost:8766/telemetry/run.jsonl";
const COMMAND_URL = "http://localhost:8765/command";

function modeLabel(mode: Mode) {
  if (mode === "mock") return "Mock live";
  if (mode === "replay") return "Replay";
  return "Live feed";
}

export function AgentSimPage({
  mode,
  setMode,
  playing,
  setPlaying,
  speed,
  setSpeed,
  cloud,
  setCloud,
  liveUrl,
  setLiveUrl,
  latest,
  stream,
  step,
  hint,
  cloudRtt,
  aggregates,
  decisions,
  resetKey,
  onReset,
  onFetchIsolatedReplay,
}: Props) {
  const [draft, setDraft] = useState("");
  const autoStepBusy = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "agent",
      text: "Nemoclaw control bridge is staged. For now, I can mirror operator intents while the sim runs locally.",
      at: "ready",
    },
  ]);

  useEffect(() => {
    if (liveUrl !== LIVE_FEED_URL) setLiveUrl(LIVE_FEED_URL);
  }, [liveUrl, setLiveUrl]);

  // Auto-step: when playing in live mode, continuously advance the sim
  useEffect(() => {
    if (!playing || mode !== "live") return;
    const id = setInterval(async () => {
      if (autoStepBusy.current) return;
      autoStepBusy.current = true;
      try {
        await fetch(COMMAND_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ steps: 1 }),
        });
      } catch {
        // sim not running — ignore
      } finally {
        autoStepBusy.current = false;
      }
    }, 600);
    return () => clearInterval(id);
  }, [playing, mode]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const at = `step ${step}`;
    setMessages((prev) => [...prev, { role: "operator", text: trimmed, at }]);
    setDraft("");

    // Make sure the dashboard is watching the live feed before the sim moves.
    if (mode !== "live") setMode("live");
    if (!playing) setPlaying(true);

    try {
      const res = await fetch(COMMAND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: trimmed, steps: 6 }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as {
        steps_run: number;
        done: boolean;
        executed: { step: number; action: string; events: string[] }[];
      };
      const last = data.executed[data.executed.length - 1];
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: `Ran ${data.steps_run} sim step${data.steps_run === 1 ? "" : "s"} on the cell${
            last ? ` — last: ${last.action}` : ""
          }${data.done ? " · task complete" : ""}. Watch the live feed.`,
          at: last ? `step ${last.step}` : at,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: `Sim bridge unreachable (${(e as Error).message}). Start the MCP sim server on :8765 (python -m factorymind.sim.a.mcp_server --http).`,
          at,
        },
      ]);
    }
  };

  const latestRow = latest.d ?? latest.a;
  const health = latestRow?.parsed_ok === false ? "Parse guard tripped" : latestRow?.sim_event ?? "Nominal";

  return (
    <main className="agent-shell">
      <section className="agent-grid">
        <div className="agent-sim-stack">
          <div className="agent-control-strip">
            <div className="agent-mode-tabs">
              {(["mock", "replay", "live"] as Mode[]).map((m) => (
                <button key={m} className={mode === m ? "is-active" : ""} onClick={() => setMode(m)}>
                  {modeLabel(m)}
                </button>
              ))}
            </div>
            <button className="agent-primary" onClick={() => setPlaying(!playing)}>
              {playing ? "Pause sim" : "Run sim"}
            </button>
            <button className="agent-secondary" onClick={onReset}>Reset</button>
            <button className="agent-secondary" onClick={onFetchIsolatedReplay}>Load replay</button>
            <div className="agent-status-inline">
              <span className="agent-status-dot" />
              <strong>{playing ? "Running" : "Paused"}</strong>
              <span>{modeLabel(mode)} · {health}</span>
            </div>
          </div>

          <div className="agent-speed-row">
            <label>
              Speed
              <input
                type="range"
                min={0.25}
                max={4}
                step={0.25}
                value={speed}
                onChange={(event) => setSpeed(parseFloat(event.target.value))}
              />
              <span>{speed.toFixed(2).replace(/0$/, "")}x</span>
            </label>
            <label className="agent-checkbox">
              <input type="checkbox" checked={cloud} onChange={(event) => setCloud(event.target.checked)} />
              Cloud comparison
            </label>
            {mode === "live" && (
              <input
                value={liveUrl}
                onChange={(event) => setLiveUrl(event.target.value)}
                className="agent-live-input"
                spellCheck={false}
                aria-label="Live telemetry URL"
              />
            )}
          </div>

          <div className="agent-sim-frame">
            <CellView
              latest={latestRow}
              step={step}
              resetKey={resetKey}
              liveMujocoFrame={mode === "live"}
              animatedFallback={mode === "mock"}
            />
          </div>

          <div className="agent-metrics-grid">
            <LatencyRace d={latest.d} a={latest.a} />
            <StatsPanel
              d={aggregates.d}
              a={aggregates.a}
              cloud={cloud}
              cloudRtt={cloudRtt}
              step={step}
              decisions={decisions}
            />
          </div>
        </div>

        <aside className="agent-chat-card">
          <div className="agent-chat-header">
            <div>
              <span>Nemoclaw console</span>
              <strong>Local command draft</strong>
            </div>
            <small>{hint}</small>
          </div>

          <div className="agent-quick-grid">
            {quickCommands.map((command) => (
              <button key={command} onClick={() => send(command)}>{command}</button>
            ))}
          </div>

          <div className="agent-thread">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`agent-message ${message.role}`}>
                <span>{message.role === "operator" ? "You" : "Nemoclaw"}</span>
                <p>{message.text}</p>
                <small>{message.at}</small>
              </div>
            ))}
          </div>

          <form
            className="agent-composer"
            onSubmit={(event) => {
              event.preventDefault();
              send(draft);
            }}
          >
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask the agent to inspect, pause, reset, or run the sim..."
              rows={4}
            />
            <button type="submit">Queue command</button>
          </form>

          <ActionStream rows={stream.slice(0, 6)} />
        </aside>
      </section>
    </main>
  );
}
