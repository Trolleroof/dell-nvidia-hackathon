import { useEffect, useState } from "react";
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

const LIVE_FEED_URL = "http://localhost:8765/telemetry/run.jsonl";
const COMMAND_URL = "http://localhost:8765/command";
const RESET_URL = "http://localhost:8765/reset";
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
  // Pre-seeded so the channel self-explains: judges see what a command looks like.
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "operator", text: "sort the green parts into station_2" },
    { role: "agent", text: "Acknowledged — r0 grips the green part, r1 holds clear. Running the cell via on-device oracle policy." },
  ]);
  const [scenario, setScenario] = useState("default");

  const pickScenario = async (id: string) => {
    setScenario(id);
    try {
      const res = await fetch(SCENARIO_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed: 0, scenario: id }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onReset();
    } catch {
      // sim server not running
    }
  };

  useEffect(() => {
    if (liveUrl !== LIVE_FEED_URL) setLiveUrl(LIVE_FEED_URL);
  }, [liveUrl, setLiveUrl]);

  const handleReset = async () => {
    setPlaying(false);
    try {
      const res = await fetch(RESET_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed: 0, scenario }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onReset();
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "Environment reset. Enter a prompt to run that exact task." },
      ]);
    } catch (e) {
      onReset();
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: `Reset failed (${(e as Error).message}). Start MCP sim server on :8765.`,
        },
      ]);
    }
  };

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
      const executed = Array.isArray(data.executed) ? data.executed : [];
      const last = executed[executed.length - 1];
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
            <button className="agent-secondary" onClick={handleReset}>Reset</button>
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
          <div className="mb-3.5 flex flex-wrap items-center gap-2 rounded-[1.8rem_1.2rem_1.6rem_1.35rem] border border-border-light bg-white/45 p-2 shadow-[0_14px_28px_-26px_rgba(93,112,82,.65)]">
            <span className="mr-1 px-2 text-[11px] font-extrabold uppercase tracking-[0.12em] text-muted-foreground">
              Scenario
            </span>
            {SCENARIOS.map(([id, label]) => (
              <button
                key={id}
                onClick={() => pickScenario(id)}
                title={`Load the "${label}" cell task / layout`}
                className={`rounded-full px-3 py-2 text-[11px] font-extrabold uppercase tracking-[0.09em] transition-all duration-300 active:scale-95 ${
                  scenario === id
                    ? "bg-nvidia text-white shadow-[0_12px_24px_-16px_rgba(93,112,82,.8)]"
                    : "border border-border-light bg-white/45 text-muted-foreground hover:-translate-y-0.5 hover:border-clay hover:text-clay"
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
