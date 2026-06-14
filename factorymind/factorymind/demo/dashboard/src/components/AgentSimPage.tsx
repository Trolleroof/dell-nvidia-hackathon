import { useEffect, useRef, useState } from "react";
import { CellView } from "./CellView";
import { MetricsPanel, ActivityLog } from "./Telemetry";
import type { TelemetryRow } from "../types";

interface ChatMessage {
  role: "operator" | "agent";
  text: string;
}

interface Props {
  playing: boolean;
  setPlaying: (playing: boolean) => void;
  speed: number;
  setSpeed: (speed: number) => void;
  liveUrl: string;
  setLiveUrl: (url: string) => void;
  latest: { d?: TelemetryRow; a?: TelemetryRow };
  stream: TelemetryRow[];
  step: number;
  resetKey: number;
  onReset: () => void;
}

const LIVE_FEED_URL = "http://localhost:8766/telemetry/run.jsonl";
const COMMAND_URL = "http://localhost:8765/command";
const SCENARIO_URL = "http://localhost:8765/scenario";

// Scenario presets the sim backend supports (id → label).
const SCENARIOS: [string, string][] = [
  ["default", "Default"],
  ["sort_green", "Sort Green"],
  ["misaligned", "Misaligned"],
  ["conveyor_feed", "Conveyor"],
  ["empty_bin", "Empty Bin"],
];

export function AgentSimPage({
  playing,
  setPlaying,
  speed,
  setSpeed,
  liveUrl,
  setLiveUrl,
  latest,
  stream,
  step,
  resetKey,
  onReset,
}: Props) {
  const [draft, setDraft] = useState("");
  const autoStepBusy = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [scenario, setScenario] = useState("default");

  const pickScenario = async (id: string) => {
    setScenario(id);
    try {
      await fetch(SCENARIO_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: id }),
      });
    } catch {
      // sim server not running
    }
  };

  useEffect(() => {
    if (liveUrl !== LIVE_FEED_URL) setLiveUrl(LIVE_FEED_URL);
  }, [liveUrl, setLiveUrl]);

  useEffect(() => {
    if (!playing) return;
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
        // sim not running
      } finally {
        autoStepBusy.current = false;
      }
    }, 600);
    return () => clearInterval(id);
  }, [playing]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages((prev) => [...prev, { role: "operator", text: trimmed }]);
    setDraft("");

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
          text: `Ran ${data.steps_run} step${data.steps_run === 1 ? "" : "s"}${last ? ` — ${last.action}` : ""}${data.done ? " · done" : ""}.`,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: `Sim unreachable (${(e as Error).message}). Start MCP sim server on :8765.`,
        },
      ]);
    }
  };

  const latestRow = latest.d ?? latest.a;
  const health = latestRow?.parsed_ok === false ? "Parse error" : latestRow?.sim_event ?? "OK";

  return (
    <main className="agent-shell">
      <div className="agent-eyebrow">
        <span>§ 01</span>
        <span>Control Room</span>
      </div>
      <section className="agent-grid">
        <div className="agent-sim-stack">
          <div className="agent-control-strip">
            <div className="agent-mode-tabs">
              <button className="is-active" aria-current="true">Live</button>
            </div>
            <button className="agent-primary" onClick={() => setPlaying(!playing)}>
              {playing ? "Pause" : "Run"}
            </button>
            <button className="agent-secondary" onClick={onReset}>Reset</button>
            <div className="agent-status-inline">
              <span className={`agent-status-dot${playing ? "" : " is-idle"}`} />
              <strong>{playing ? "Running" : "Paused"}</strong>
              <span>Live · {health}</span>
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
          </div>

          {/* Scenario switcher — swap the cell's task / layout */}
          <div className="mb-3.5 flex flex-wrap items-center gap-2">
            <span className="mr-1 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Scenario
            </span>
            {SCENARIOS.map(([id, label]) => (
              <button
                key={id}
                onClick={() => pickScenario(id)}
                title={`Load the "${label}" cell task / layout`}
                className={`border px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] transition-colors duration-100 ${
                  scenario === id
                    ? "border-nvidia bg-nvidia text-background"
                    : "border-border-light text-muted-foreground hover:border-foreground hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="agent-sim-frame">
            <CellView
              latest={latestRow}
              step={step}
              resetKey={resetKey}
              liveMujocoFrame
            />
          </div>

          {/* Tier 1 + Tier 2 telemetry */}
          <div className="mt-4 grid gap-4">
            <MetricsPanel d={latest.d} a={latest.a} />
            <ActivityLog stream={stream} />
          </div>
        </div>

        <aside className="agent-chat-card">
          <div className="agent-chat-header">
            <strong>Operator Channel</strong>
            <span className="agent-chat-sub">Natural language → oracle policy</span>
          </div>

          <div className="agent-thread">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`agent-message ${message.role}`}>
                <span>{message.role === "operator" ? "You" : "Agent"}</span>
                <p>{message.text}</p>
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
              placeholder="Command..."
              rows={4}
            />
            <button type="submit">Send →</button>
          </form>
        </aside>
      </section>
    </main>
  );
}
