import { useEffect, useRef, useState } from "react";
import type { TelemetryRow } from "../types";

interface Arm {
  x: number;
  base: number;
  angle: number;
  grip: boolean;
}
interface Part {
  id: string;
  x: number;
  y: number;
  placed: boolean;
}
interface SimPart {
  id: string;
  at: string;
  color: string;
}

const BINS: [string, number, number][] = [
  ["bin_a", 415, 70],
  ["bin_b", 415, 130],
  ["station_1", 415, 190],
];

// Monochrome: part identity reads from labels + fill treatment, never hue.
const PART_COLORS: Record<string, string> = {
  part_1: "#ffffff",
  part_2: "#ffffff",
  part_3: "#ffffff",
};

const ZONES = ["bin_a", "bin_b", "station_1", "station_2"];

export const SIM_FRAME_BASE = "http://localhost:8766";
const SIM_API_BASE = "http://localhost:8765";

export function CellView({
  latest,
  step,
  resetKey,
  frameBase = SIM_FRAME_BASE,
  preferMujocoFrame = false,
  liveMujocoFrame = false,
  animatedFallback = false,
}: {
  latest?: TelemetryRow;
  step: number;
  resetKey: number;
  frameBase?: string;
  preferMujocoFrame?: boolean;
  liveMujocoFrame?: boolean;
  animatedFallback?: boolean;
}) {
  const [arms, setArms] = useState<Arm[]>([
    { x: 150, base: 250, angle: -0.5, grip: false },
    { x: 370, base: 250, angle: 0.5, grip: false },
  ]);
  const placedRef = useRef(0);
  const [parts, setParts] = useState<Part[]>([
    { id: "part_1", x: 200, y: 230, placed: false },
    { id: "part_2", x: 260, y: 235, placed: false },
    { id: "part_3", x: 320, y: 232, placed: false },
  ]);
  const [frameRefresh, setFrameRefresh] = useState(0);
  const [mockTick, setMockTick] = useState(0);
  const [simParts, setSimParts] = useState<SimPart[]>([]);
  const [dragOver, setDragOver] = useState<string | null>(null);
  const [teleporting, setTeleporting] = useState(false);

  const effectiveStep = latest ? step : mockTick;
  const replayStep = String(effectiveStep % 13).padStart(4, "0");
  // Live mode consumes the server's continuous 60fps MJPEG stream (one persistent
  // <img> connection) instead of re-fetching latest.png — `streamNonce` is only
  // bumped to force a reconnect after an error.
  const [streamNonce, setStreamNonce] = useState(0);
  const liveStreamSrc = `${SIM_API_BASE}/sim/stream.mjpg${streamNonce ? `?r=${streamNonce}` : ""}`;
  const pollPath = latest?.frame_url ?? (preferMujocoFrame ? `/sim/replay/step_${replayStep}.png` : undefined);
  const pollSrc = pollPath ? `${frameBase}${pollPath}?step=${effectiveStep}&refresh=${frameRefresh}` : undefined;
  const frameSrc = liveMujocoFrame ? liveStreamSrc : pollSrc;
  const [failedFrameSrc, setFailedFrameSrc] = useState<string | null>(null);
  const showFrame = Boolean(frameSrc && failedFrameSrc !== frameSrc);

  // reset on resetKey change
  useEffect(() => {
    placedRef.current = 0;
    setParts([
      { id: "part_1", x: 200, y: 230, placed: false },
      { id: "part_2", x: 260, y: 235, placed: false },
      { id: "part_3", x: 320, y: 232, placed: false },
    ]);
  }, [resetKey]);

  // Live view is a continuous MJPEG stream — no polling. If it errors (server
  // not up yet), retry the connection every few seconds.
  useEffect(() => {
    if (!liveMujocoFrame || failedFrameSrc === null) return;
    const id = window.setInterval(() => {
      setFailedFrameSrc(null);
      setStreamNonce((n) => n + 1);
    }, 3000);
    return () => window.clearInterval(id);
  }, [liveMujocoFrame, failedFrameSrc]);

  useEffect(() => {
    if (!animatedFallback || latest) return;
    const id = window.setInterval(() => setMockTick((n) => n + 1), 650);
    return () => window.clearInterval(id);
  }, [animatedFallback, latest]);

  // Poll sim state from MCP server for part positions (interactive controls)
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${SIM_API_BASE}/sim/state`, { cache: "no-store" });
        if (!res.ok) return;
        const state = await res.json();
        if (Array.isArray(state.parts)) {
          setSimParts(state.parts.map((p: { id: string; at: string; color?: string }) => ({
            id: p.id,
            at: p.at,
            color: PART_COLORS[p.id] ?? "#888",
          })));
        }
      } catch {
        // MCP server not running – interactive controls stay hidden
      }
    };
    poll();
    const id = window.setInterval(poll, 500);
    return () => window.clearInterval(id);
  }, []);

  // react to each new decision, or animate locally when no backend feed is attached
  useEffect(() => {
    if (!latest && !animatedFallback) return;
    const phase = effectiveStep * 0.42;
    setArms([
      { x: 150, base: 250, angle: -0.65 + Math.sin(phase) * 0.75, grip: effectiveStep % 4 > 1 },
      { x: 370, base: 250, angle: 0.55 + Math.cos(phase * 0.9) * 0.8, grip: effectiveStep % 5 > 2 },
    ]);
    if (effectiveStep > 0 && effectiveStep % 3 === 0) {
      setParts((prev) => {
        const idx = prev.findIndex((p) => !p.placed);
        if (idx < 0) {
          placedRef.current = 0;
          return [
            { id: "part_1", x: 200, y: 230, placed: false },
            { id: "part_2", x: 260, y: 235, placed: false },
            { id: "part_3", x: 320, y: 232, placed: false },
          ];
        }
        const n = [...prev];
        n[idx] = { ...n[idx], placed: true, x: 430 + placedRef.current * 12, y: 90 + placedRef.current * 30 };
        placedRef.current += 1;
        return n;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveStep, animatedFallback, latest]);

  const handleTeleport = async (partId: string, target: string) => {
    if (teleporting) return;
    setTeleporting(true);
    try {
      await fetch(`${SIM_API_BASE}/teleport_part`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ part_id: partId, target }),
      });
      // Refresh frame immediately after teleport
      setFrameRefresh((n) => n + 1);
    } catch {
      // ignore
    } finally {
      setTeleporting(false);
    }
  };

  const placedCount = simParts.length > 0
    ? simParts.filter((p) => p.at === "station_1" || p.at === "station_2").length
    : Math.min(placedRef.current, 3);

  return (
    <div className="card">
      <h2 className="card-title">
        <span className="tick" />
        Assembly Cell · 2 Arms
        {showFrame && <span className="ml-auto pill border-nvidia bg-nvidia text-background">MuJoCo</span>}
        {!showFrame && animatedFallback && <span className="ml-auto pill">Mock live</span>}
      </h2>
      {showFrame && frameSrc ? (
        <div className="group relative border border-foreground transition-all duration-100 hover:border-2">
          <img
            src={frameSrc}
            alt={`MuJoCo sim frame step ${effectiveStep}`}
            className="block w-full h-[300px] object-cover bg-background"
            onError={() => setFailedFrameSrc(frameSrc)}
          />
          <div className={`absolute left-0 top-0 px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-background ${liveMujocoFrame ? "bg-nvidia" : "bg-foreground"}`}>
            {liveMujocoFrame ? "Live · MuJoCo" : "MuJoCo Frame"}
          </div>
        </div>
      ) : (
      <svg
        viewBox="0 0 520 300"
        className="w-full h-[300px] border border-border-light bg-background"
      >
        {/* conveyor rule */}
        <rect x={60} y={248} width={400} height={14} fill="#000000" stroke="#ffffff" strokeOpacity={0.3} />
        <line x1={40} y1={262} x2={480} y2={262} stroke="#ffffff" strokeOpacity={0.2} strokeWidth={2} />
        {BINS.map(([name, x, y]) => (
          <g key={name}>
            <rect x={x} y={y} width={78} height={44} fill="none" stroke="#ffffff" strokeOpacity={0.55} />
            <text x={x + 39} y={y + 27} fill="#ffffff" fontSize={10} textAnchor="middle"
              fontFamily="'JetBrains Mono', monospace" letterSpacing={1} fontWeight={600}>{name}</text>
          </g>
        ))}
        {arms.map((a, i) => {
          const c = i === 0 ? "#8fdc00" : "#2fa4de";
          const seg1 = 70, seg2 = 58;
          const jx = a.x + Math.sin(a.angle) * seg1;
          const jy = a.base - Math.cos(a.angle) * seg1;
          const handAng = a.angle + (a.grip ? 0.7 : 0.3);
          const hx = jx + Math.sin(handAng) * seg2;
          const hy = jy - Math.cos(handAng) * seg2 * 0.6;
          const hs = a.grip ? 14 : 10;
          return (
            <g key={i} style={{ transition: "all .1s linear" }}>
              {/* sharp squares, not circles — architectural geometry */}
              <rect x={a.x - 12} y={a.base - 12} width={24} height={24} fill="#000000" stroke={c} strokeWidth={1.5} />
              <line x1={a.x} y1={a.base} x2={jx} y2={jy} stroke={c} strokeWidth={6} strokeLinecap="butt" />
              <line x1={jx} y1={jy} x2={hx} y2={hy} stroke={c} strokeWidth={4} strokeLinecap="butt" opacity={0.9} />
              <rect x={jx - 4} y={jy - 4} width={8} height={8} fill={c} />
              <rect x={hx - hs / 2} y={hy - hs / 2} width={hs} height={hs} fill={a.grip ? c : "#000000"} stroke={c} strokeWidth={1.5} />
              <text x={a.x} y={a.base + 24} fill={c} fontSize={10} textAnchor="middle"
                fontFamily="'JetBrains Mono', monospace" fontWeight={600}>r{i}</text>
            </g>
          );
        })}
        {/* placed = solid white, in-flight = hollow outline */}
        {parts.map((p) => (
          <rect key={p.id} x={p.x - 7} y={p.y - 7} width={14} height={14}
            fill={p.placed ? "#ffffff" : "none"} stroke="#ffffff" strokeWidth={1.5}
            style={{ transition: "all .1s linear" }} />
        ))}
      </svg>
      )}

      <div className="mt-4 grid grid-cols-3 border-t border-border-light pt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
        <div className="flex flex-col gap-1 pr-3">
          <span>Step</span>
          <b className="font-display text-xl font-semibold tabular-nums text-foreground">{effectiveStep}</b>
        </div>
        <div className="flex flex-col gap-1 border-l border-border-light px-3">
          <span>Event</span>
          <b className="truncate text-[12px] font-semibold normal-case tracking-normal text-foreground">{latest?.sim_event ?? (animatedFallback ? "mock_cycle" : "—")}</b>
        </div>
        <div className="flex flex-col gap-1 border-l border-border-light pl-3">
          <span>Placed</span>
          <b className="font-display text-xl font-semibold tabular-nums text-foreground">{placedCount} / 3</b>
        </div>
      </div>

      {/* Interactive Part Controls — shown when sim state is available */}
      {simParts.length > 0 && (
        <div className="mt-4 border-t-2 border-border pt-4">
          <div className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Part Controls — drag to move
          </div>
          <div className="flex items-start gap-4">
            {/* Draggable part sources */}
            <div className="flex min-w-[120px] flex-col gap-1.5">
              {simParts.map((part, i) => (
                <div
                  key={part.id}
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData("part_id", part.id)}
                  className="group flex cursor-grab select-none items-center gap-2 border border-border bg-background px-2 py-1.5 transition-colors duration-100 hover:bg-foreground hover:text-background"
                  title={`Drag ${part.id} to a zone`}
                >
                  {/* index square — identity by number, not hue */}
                  <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center border border-border font-mono text-[9px] font-semibold group-hover:border-background">
                    {i + 1}
                  </span>
                  <span className="font-mono text-[11px] text-foreground group-hover:text-background">{part.id}</span>
                  <span className="ml-auto truncate font-mono text-[9px] text-muted-foreground group-hover:text-background">@{part.at}</span>
                </div>
              ))}
            </div>

            <div className="self-center px-1 font-mono text-base text-muted-foreground">→</div>

            {/* Drop zones — invert on drag-over (emphasis = inversion) */}
            <div className="grid flex-1 grid-cols-2 gap-1.5">
              {ZONES.map((zone) => {
                const active = dragOver === zone;
                return (
                  <div
                    key={zone}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(zone); }}
                    onDragLeave={() => setDragOver(null)}
                    onDrop={(e) => {
                      e.preventDefault();
                      const partId = e.dataTransfer.getData("part_id");
                      setDragOver(null);
                      if (partId) handleTeleport(partId, zone);
                    }}
                    className={`cursor-default border px-2 py-2 text-center font-mono text-[10px] uppercase tracking-[0.1em] transition-colors duration-100 ${
                      active
                        ? "border-nvidia bg-nvidia text-background"
                        : "border-border-light text-muted-foreground"
                    }`}
                  >
                    {zone}
                  </div>
                );
              })}
            </div>
          </div>
          {teleporting && (
            <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Moving part…</div>
          )}
        </div>
      )}
    </div>
  );
}
