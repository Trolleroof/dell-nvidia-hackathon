import { useEffect, useRef, useState } from "react";
import { ActionStream } from "./ActionStream";
import { CellView } from "./CellView";
import { LatencyRace } from "./LatencyRace";
import { StatsPanel } from "./StatsPanel";
import type { TelemetryRow, Aggregate } from "../types";

interface ChatMessage {
  role: "operator" | "agent";
  text: string;
  at?: string;
}

interface Props {
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
}

const quickCommands = [
  "Run five safe assembly steps",
  "Pause on collision or parse failure",
  "Explain the last action",
];

const LIVE_FEED_URL = "http://localhost:8766/telemetry/run.jsonl";
const COMMAND_URL = "http://localhost:8765/command";

export function AgentSimPage({
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
}: Props) {
  const [draft, setDraft] = useState("");
  const autoStepBusy = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

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
      const at = step > 0 ? `step ${step}` : "live";
      const res = await fetch(COMMAND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: trimmed, steps: 6 }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as {
        streaming?: boolean;
        queued_steps?: number;
        steps_run?: number;
        done?: boolean;
        executed?: { step: number; action: string; events: string[] }[];
      };
      if (data.streaming) {
        const n = data.queued_steps ?? 0;
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            text: `Queued ${n} sim step${n === 1 ? "" : "s"} - driving the cell oracle. Watch the live stream.`,
            at,
          },
        ]);
      } else {
        const executed = data.executed ?? [];
        const last = executed[executed.length - 1];
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            text: `Ran ${data.steps_run ?? 0} sim step${data.steps_run === 1 ? "" : "s"} on the cell${
              last ? ` - last: ${last.action}` : ""
            }${data.done ? " - task complete" : ""}. Watch the live feed.`,
            at: last ? `step ${last.step}` : at,
          },
        ]);
      }
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
      <section className="agent-grid">
        <div className="agent-sim-stack">
          <div className="agent-control-strip">
            <div className="agent-status-inline">
              <span className={`agent-status-dot${playing ? "" : " is-idle"}`} />
              <strong>{playing ? "Running" : "Paused"}</strong>
              <span>Live feed - {health}</span>
            </div>
            <button className="agent-primary" onClick={() => setPlaying(!playing)}>
              {playing ? "Pause" : "Run"}
            </button>
            <button className="agent-secondary" onClick={onReset}>Reset</button>
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
            <label className="inline-flex items-center gap-2 border border-border px-3 py-2 text-foreground">
              <input type="checkbox" checked={cloud} onChange={(event) => setCloud(event.target.checked)} />
              Cloud comparison
            </label>
            <input
              value={liveUrl}
              onChange={(event) => setLiveUrl(event.target.value)}
              className="min-w-[280px] flex-1 border border-border bg-transparent px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground"
              spellCheck={false}
              aria-label="Live telemetry URL"
            />
          </div>

          <div className="agent-sim-frame">
            <CellView
              latest={latestRow}
              step={step}
              resetKey={resetKey}
              liveMujocoFrame
              animatedFallback
            />
          </div>
        </div>

        <aside className="agent-chat-card">
          <div className="agent-chat-header">
            <strong>Chat</strong>
            <span className="agent-chat-sub">{hint}</span>
          </div>

          <div className="agent-thread">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`agent-message ${message.role}`}>
                <span>{message.role === "operator" ? "You" : "Agent"}{message.at ? ` - ${message.at}` : ""}</span>
                <p>{message.text}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {quickCommands.map((command) => (
              <button
                key={command}
                type="button"
                className="agent-secondary px-3 py-2 text-[10px]"
                onClick={() => send(command)}
              >
                {command}
              </button>
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
            <button type="submit">Send</button>
          </form>
        </aside>
      </section>

      <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_380px]">
        <div className="flex flex-col gap-4">
          <LatencyRace d={latest.d} a={latest.a} />
          <ActionStream rows={stream} />
        </div>
        <StatsPanel
          d={aggregates.d}
          a={aggregates.a}
          cloud={cloud}
          cloudRtt={cloudRtt}
          step={step}
          decisions={decisions}
        />
      </section>
    </main>
  );
}
