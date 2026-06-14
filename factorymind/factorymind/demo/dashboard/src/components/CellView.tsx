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
  c: string;
}
interface SimPart {
  id: string;
  at: string;
  color: string;
}

const BINS: [string, number, number, string][] = [
  ["bin_a", 415, 70, "#76b900"],
  ["bin_b", 415, 130, "#38b6ff"],
  ["station_1", 415, 190, "#b06bff"],
];

const PART_COLORS: Record<string, string> = {
  part_1: "#ffb02e",
  part_2: "#38b6ff",
  part_3: "#76b900",
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
    { id: "part_1", x: 200, y: 230, placed: false, c: "#ffb02e" },
    { id: "part_2", x: 260, y: 235, placed: false, c: "#38b6ff" },
    { id: "part_3", x: 320, y: 232, placed: false, c: "#76b900" },
  ]);
  const [frameRefresh, setFrameRefresh] = useState(0);
  const [mockTick, setMockTick] = useState(0);
  const [simParts, setSimParts] = useState<SimPart[]>([]);
  const [dragOver, setDragOver] = useState<string | null>(null);
  const [teleporting, setTeleporting] = useState(false);

  const effectiveStep = latest ? step : mockTick;
  const replayStep = String(effectiveStep % 13).padStart(4, "0");
  const framePath = liveMujocoFrame
    ? "/sim/latest.png"
    : latest?.frame_url ?? (preferMujocoFrame ? `/sim/replay/step_${replayStep}.png` : undefined);
  const frameSrc = framePath ? `${frameBase}${framePath}?step=${effectiveStep}&refresh=${frameRefresh}` : undefined;
  const [failedFrameSrc, setFailedFrameSrc] = useState<string | null>(null);
  const showFrame = Boolean(frameSrc && failedFrameSrc !== frameSrc);

  // reset on resetKey change
  useEffect(() => {
    placedRef.current = 0;
    setParts([
      { id: "part_1", x: 200, y: 230, placed: false, c: "#ffb02e" },
      { id: "part_2", x: 260, y: 235, placed: false, c: "#38b6ff" },
      { id: "part_3", x: 320, y: 232, placed: false, c: "#76b900" },
    ]);
  }, [resetKey]);

  // Fast frame refresh: 100ms for smooth live view
  useEffect(() => {
    if (!liveMujocoFrame) return;
    const id = window.setInterval(() => setFrameRefresh((n) => n + 1), 100);
    return () => window.clearInterval(id);
  }, [liveMujocoFrame]);

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
            { id: "part_1", x: 200, y: 230, placed: false, c: "#ffb02e" },
            { id: "part_2", x: 260, y: 235, placed: false, c: "#38b6ff" },
            { id: "part_3", x: 320, y: 232, placed: false, c: "#76b900" },
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
        {showFrame && <span className="ml-auto pill text-nvidia bg-[rgba(118,185,0,.12)]">MuJoCo</span>}
        {!showFrame && animatedFallback && <span className="ml-auto pill text-dell-bright bg-[rgba(10,143,220,.14)]">Mock live</span>}
      </h2>
      {showFrame && frameSrc ? (
        <div className="relative">
          <img
            src={frameSrc}
            alt={`MuJoCo sim frame step ${effectiveStep}`}
            className="w-full h-[300px] rounded-xl object-cover border border-line bg-[#05080c]"
            onError={() => setFailedFrameSrc(frameSrc)}
          />
          <div className="absolute left-3 top-3 rounded-full border border-[rgba(118,185,0,.45)] bg-black/60 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-[1px] text-nvidia-bright">
            {liveMujocoFrame ? "Live MuJoCo" : "MuJoCo frame"}
          </div>
        </div>
      ) : (
      <svg
        viewBox="0 0 520 300"
        className="w-full h-[300px] rounded-xl"
        style={{ background: "radial-gradient(600px 300px at 50% 0%, #0d141c, #05080c)" }}
      >
        <rect x={60} y={248} width={400} height={14} rx={4} fill="#0e1620" stroke="#1c2430" />
        <line x1={40} y1={262} x2={480} y2={262} stroke="#162030" strokeWidth={2} />
        {BINS.map(([name, x, y, c]) => (
          <g key={name}>
            <rect x={x} y={y} width={78} height={44} rx={6} fill="rgba(255,255,255,.02)" stroke={c} strokeOpacity={0.5} />
            <text x={x + 39} y={y + 27} fill={c} fontSize={11} textAnchor="middle" fontWeight={700}>{name}</text>
          </g>
        ))}
        {arms.map((a, i) => {
          const c = i === 0 ? "#76b900" : "#0a8fdc";
          const seg1 = 70, seg2 = 58;
          const jx = a.x + Math.sin(a.angle) * seg1;
          const jy = a.base - Math.cos(a.angle) * seg1;
          const handAng = a.angle + (a.grip ? 0.7 : 0.3);
          const hx = jx + Math.sin(handAng) * seg2;
          const hy = jy - Math.cos(handAng) * seg2 * 0.6;
          return (
            <g key={i} style={{ transition: "all .3s ease" }}>
              <circle cx={a.x} cy={a.base} r={12} fill="#0e1620" stroke={c} strokeWidth={2} />
              <line x1={a.x} y1={a.base} x2={jx} y2={jy} stroke={c} strokeWidth={7} strokeLinecap="round" />
              <line x1={jx} y1={jy} x2={hx} y2={hy} stroke={c} strokeWidth={5} strokeLinecap="round" opacity={0.9} />
              <circle cx={jx} cy={jy} r={5} fill={c} />
              <circle cx={hx} cy={hy} r={a.grip ? 7 : 5} fill={a.grip ? c : "#0e1620"} stroke={c} strokeWidth={2} />
              <text x={a.x} y={a.base + 22} fill={c} fontSize={10} textAnchor="middle" fontWeight={700}>r{i}</text>
            </g>
          );
        })}
        {parts.map((p) => (
          <rect key={p.id} x={p.x - 7} y={p.y - 7} width={14} height={14} rx={3} fill={p.c}
            opacity={p.placed ? 1 : 0.85} stroke={p.placed ? "#fff" : "none"} strokeOpacity={0.25}
            style={{ transition: "all .4s ease" }} />
        ))}
      </svg>
      )}

      <div className="flex gap-3.5 flex-wrap mt-3 text-xs text-dim">
        <span>Step <b className="text-text">{effectiveStep}</b></span>
        <span>Event <b className="text-text">{latest?.sim_event ?? (animatedFallback ? "mock_cycle" : "—")}</b></span>
        <span>Parts placed <b className="text-text">{placedCount} / 3</b></span>
      </div>

      {/* Interactive Part Controls — shown when sim state is available */}
      {simParts.length > 0 && (
        <div className="mt-3 rounded-xl border border-line/60 p-3 bg-[rgba(255,255,255,.02)]">
          <div className="text-[10px] font-extrabold uppercase tracking-wider text-dim mb-2.5">
            Part Controls — drag to move
          </div>
          <div className="flex gap-3 items-start">
            {/* Draggable part sources */}
            <div className="flex flex-col gap-1.5 min-w-[110px]">
              {simParts.map((part) => (
                <div
                  key={part.id}
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData("part_id", part.id)}
                  className="flex items-center gap-1.5 px-2 py-1 rounded-lg cursor-grab border border-line/50 bg-[#0e1620] hover:bg-[#111820] select-none"
                  title={`Drag ${part.id} to a zone`}
                >
                  <span
                    className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                    style={{ background: part.color }}
                  />
                  <span className="text-[11px] font-mono text-text">{part.id}</span>
                  <span className="text-[9px] text-dim ml-auto truncate">@{part.at}</span>
                </div>
              ))}
            </div>

            <div className="self-center text-dim text-sm px-1">→</div>

            {/* Drop zones */}
            <div className="grid grid-cols-2 gap-1.5 flex-1">
              {ZONES.map((zone) => {
                const zoneColor =
                  zone === "station_1" || zone === "station_2"
                    ? "#b06bff"
                    : zone === "bin_b"
                    ? "#38b6ff"
                    : "#76b900";
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
                    className="px-2 py-2 rounded-lg border text-[10px] font-mono text-center transition-all duration-150 cursor-default"
                    style={{
                      borderColor: dragOver === zone ? zoneColor : "rgba(255,255,255,.1)",
                      background: dragOver === zone ? `${zoneColor}18` : "transparent",
                      color: dragOver === zone ? zoneColor : "#6b7a8d",
                    }}
                  >
                    {zone}
                  </div>
                );
              })}
            </div>
          </div>
          {teleporting && (
            <div className="mt-2 text-[10px] text-dim">Moving part…</div>
          )}
        </div>
      )}
    </div>
  );
}
