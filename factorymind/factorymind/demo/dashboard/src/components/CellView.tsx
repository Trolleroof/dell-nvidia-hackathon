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

const BINS: [string, number, number, string][] = [
  ["bin_a", 415, 70, "#76b900"],
  ["bin_b", 415, 130, "#38b6ff"],
  ["station_1", 415, 190, "#b06bff"],
];

export const SIM_FRAME_BASE = "http://localhost:8766";

export function CellView({
  latest,
  step,
  resetKey,
  frameBase = SIM_FRAME_BASE,
}: {
  latest?: TelemetryRow;
  step: number;
  resetKey: number;
  frameBase?: string;
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

  // reset on resetKey change
  useEffect(() => {
    placedRef.current = 0;
    setParts([
      { id: "part_1", x: 200, y: 230, placed: false, c: "#ffb02e" },
      { id: "part_2", x: 260, y: 235, placed: false, c: "#38b6ff" },
      { id: "part_3", x: 320, y: 232, placed: false, c: "#76b900" },
    ]);
  }, [resetKey]);

  // react to each new decision
  useEffect(() => {
    if (!latest) return;
    setArms((prev) => prev.map((a) => ({ ...a, angle: -0.8 + Math.random() * 1.6, grip: Math.random() < 0.5 })));
    if (Math.random() < 0.22) {
      setParts((prev) => {
        const idx = prev.findIndex((p) => !p.placed);
        if (idx < 0) return prev;
        const n = [...prev];
        n[idx] = { ...n[idx], placed: true, x: 430 + placedRef.current * 12, y: 90 + placedRef.current * 30 };
        placedRef.current += 1;
        return n;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  return (
    <div className="card">
      <h2 className="card-title"><span className="tick" />Assembly Cell · 2 Arms</h2>
      {latest?.frame_url ? (
        <img
          src={`${frameBase}${latest.frame_url}`}
          alt={`Sim frame step ${step}`}
          className="w-full h-[300px] rounded-xl object-cover border border-line bg-[#05080c]"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
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
        <span>Step <b className="text-text">{step}</b></span>
        <span>Event <b className="text-text">{latest?.sim_event ?? "—"}</b></span>
        <span>Parts placed <b className="text-text">{placedRef.current} / 3</b></span>
      </div>
    </div>
  );
}
