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

export const SIM_API_BASE = "http://localhost:8765";
export const SIM_FRAME_BASE = SIM_API_BASE;

// ── Smooth live canvas ─────────────────────────────────────────────────────────

// Named pose → (x, y) gripper-tip pixel in a 520×300 canvas
const POSE_XY: Record<string, [number, number]> = {
  home:                [260, 42],
  above_bin_a:         [88,  192],
  above_bin_b:         [88,  137],
  above_part_1:        [76,  206],
  above_part_2:        [90,  208],
  above_part_3:        [104, 206],
  above_station_1:     [432, 192],
  above_station_2:     [432, 137],
  above_conveyor_pick: [200, 255],
  bin_a:               [88,  192],
  bin_b:               [88,  137],
  part_1:              [76,  206],
  part_2:              [90,  208],
  part_3:              [104, 206],
  station_1:           [432, 192],
  station_2:           [432, 137],
  conveyor:            [200, 255],
  conveyor_pick:       [200, 255],
};

// Where parts rest visually when at a zone (3 slots per zone)
const ZONE_SLOTS: Record<string, [number, number][]> = {
  bin_a:     [[76, 220], [90, 222], [104, 220]],
  bin_b:     [[76, 160], [90, 162], [104, 160]],
  station_1: [[418, 220], [432, 222], [446, 220]],
  station_2: [[418, 160], [432, 162], [446, 160]],
};

const ROBOT_BASES: [number, number][] = [
  [165, 272],
  [355, 272],
];

const ARM_COLORS = ["#76b900", "#0a8fdc"];
const PART_ORDER = ["part_1", "part_2", "part_3"];

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * Math.min(t, 1);
}

function poseXY(pose: string): [number, number] {
  return POSE_XY[pose] ?? POSE_XY.home;
}

function slotXY(partId: string, at: string): [number, number] {
  const slots = ZONE_SLOTS[at];
  if (slots) {
    const idx = PART_ORDER.indexOf(partId);
    return slots[Math.max(0, idx)] ?? slots[0];
  }
  return [260, 220];
}

interface ArmAnim { x: number; y: number; grip: boolean }
interface PartAnim { id: string; x: number; y: number; at: string; color: string }

function heldPartXY(arm: ArmAnim): [number, number] {
  return [arm.x, arm.y + 18];
}

function drawScene(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  arms: ArmAnim[],
  parts: PartAnim[],
  step: number,
  done: boolean,
) {
  // Background
  const bg = ctx.createRadialGradient(w / 2, 0, 10, w / 2, 0, 520);
  bg.addColorStop(0, "#0d141c");
  bg.addColorStop(1, "#05080c");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);

  // Floor rail
  ctx.fillStyle = "#0e1620";
  ctx.strokeStyle = "#1c2430";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(58, 268, 404, 12, 4);
  ctx.fill();
  ctx.stroke();
  ctx.strokeStyle = "#162030";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(38, 272);
  ctx.lineTo(482, 272);
  ctx.stroke();

  // Zone boxes
  const zones: [string, number, number, number, number, string][] = [
    ["bin_a",     55,  192, 70, 48, "#76b900"],
    ["bin_b",     55,  132, 70, 48, "#38b6ff"],
    ["station_1", 397, 192, 70, 48, "#b06bff"],
    ["station_2", 397, 132, 70, 48, "#b06bff"],
  ];
  for (const [name, x, y, bw, bh, c] of zones) {
    ctx.save();
    ctx.globalAlpha = 0.06;
    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.roundRect(x, y, bw, bh, 6);
    ctx.fill();
    ctx.restore();
    ctx.strokeStyle = c;
    ctx.globalAlpha = 0.45;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(x, y, bw, bh, 6);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.fillStyle = c;
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "center";
    ctx.fillText(name, x + bw / 2, y + bh / 2 + 4);
  }

  // Parts (draw before arms so arms sit on top)
  for (const p of parts) {
    ctx.fillStyle = p.color;
    ctx.strokeStyle = "rgba(255,255,255,0.25)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(p.x - 8, p.y - 8, 16, 16, 3);
    ctx.fill();
    ctx.stroke();
  }

  // Arms
  for (let i = 0; i < arms.length; i++) {
    const arm = arms[i];
    const [bx, by] = ROBOT_BASES[i];
    const c = ARM_COLORS[i];
    const tx = arm.x, ty = arm.y;

    // Elbow — midpoint pushed up proportional to reach distance
    const dist = Math.hypot(tx - bx, ty - by);
    const mx = (bx + tx) / 2;
    const my = (by + ty) / 2 - dist * 0.28;

    // Upper segment
    ctx.strokeStyle = c;
    ctx.lineWidth = 7;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(mx, my);
    ctx.stroke();

    // Lower segment
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(mx, my);
    ctx.lineTo(tx, ty);
    ctx.stroke();

    // Elbow joint
    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.arc(mx, my, 5, 0, Math.PI * 2);
    ctx.fill();

    // Base
    ctx.fillStyle = "#0e1620";
    ctx.strokeStyle = c;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(bx, by, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = c;
    ctx.font = "bold 9px monospace";
    ctx.textAlign = "center";
    ctx.fillText(`r${i}`, bx, by + 22);

    // Gripper
    const gripR = arm.grip ? 8 : 5;
    ctx.fillStyle = arm.grip ? c : "#0e1620";
    ctx.strokeStyle = c;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(tx, ty, gripR, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Gripper tines stay visible: open tines reach down, closed tines clamp the carried block.
    ctx.strokeStyle = c;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    if (arm.grip) {
      ctx.moveTo(tx - 9, ty + 8);
      ctx.lineTo(tx - 9, ty + 24);
      ctx.lineTo(tx - 5, ty + 27);
      ctx.moveTo(tx + 9, ty + 8);
      ctx.lineTo(tx + 9, ty + 24);
      ctx.lineTo(tx + 5, ty + 27);
    } else {
      ctx.moveTo(tx - 6, ty + 5);
      ctx.lineTo(tx - 11, ty + 18);
      ctx.moveTo(tx + 6, ty + 5);
      ctx.lineTo(tx + 11, ty + 18);
    }
    ctx.stroke();
  }

  // HUD
  ctx.fillStyle = "rgba(0,0,0,0.45)";
  ctx.beginPath();
  ctx.roundRect(8, 8, 120, 22, 4);
  ctx.fill();
  ctx.fillStyle = done ? "#ffd700" : "#00ff88";
  ctx.font = "bold 10px monospace";
  ctx.textAlign = "left";
  ctx.fillText(done ? `✓ DONE  step ${step}` : `● LIVE  step ${step}`, 14, 23);
}

function LiveSmoothCanvas({ apiBase }: { apiBase: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stepRef = useRef(0);
  const doneRef = useRef(false);

  // Animated (current) state — refs so no React re-renders on every frame
  const armCur = useRef<ArmAnim[]>([
    { x: POSE_XY.home[0], y: POSE_XY.home[1], grip: false },
    { x: POSE_XY.home[0], y: POSE_XY.home[1], grip: false },
  ]);
  const armTgt = useRef<ArmAnim[]>([
    { x: POSE_XY.home[0], y: POSE_XY.home[1], grip: false },
    { x: POSE_XY.home[0], y: POSE_XY.home[1], grip: false },
  ]);
  const partsCur = useRef<PartAnim[]>(
    PART_ORDER.map((id) => ({
      id,
      color: PART_COLORS[id] ?? "#888",
      at: "bin_a",
      x: slotXY(id, "bin_a")[0],
      y: slotXY(id, "bin_a")[1],
    })),
  );
  const partsTgt = useRef<PartAnim[]>(partsCur.current.map((p) => ({ ...p })));
  const rafRef = useRef(0);
  const prevTimeRef = useRef(0);

  // Poll sim state → update targets only
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${apiBase}/sim/state`, { cache: "no-store" });
        if (!res.ok) return;
        const s = await res.json();
        stepRef.current = s.step ?? 0;
        doneRef.current = s.done ?? false;

        // Arm targets
        (s.robots ?? []).forEach((r: { id: number; pose: string; gripper: string }) => {
          const [tx, ty] = poseXY(r.pose);
          armTgt.current[r.id] = { x: tx, y: ty, grip: r.gripper === "closed" };
        });

        // Part targets
        (s.parts ?? []).forEach((p: { id: string; at: string }) => {
          const t = partsTgt.current.find((pt) => pt.id === p.id);
          if (!t) return;
          t.at = p.at;
          if (!p.at.startsWith("gripper_")) {
            const [px, py] = slotXY(p.id, p.at);
            t.x = px;
            t.y = py;
          }
          // gripper-held parts are updated every frame in the loop below
        });
      } catch {
        // MCP not running
      }
    };
    poll();
    const id = window.setInterval(poll, 350);
    return () => window.clearInterval(id);
  }, [apiBase]);

  // RAF animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;

    const loop = (time: number) => {
      const dt = Math.min((time - (prevTimeRef.current || time)) / 1000, 0.05);
      prevTimeRef.current = time;

      // Spring-like lerp — τ ≈ 0.18 s → smooth in ~400 ms
      const alpha = 1 - Math.exp(-dt / 0.18);

      // Lerp arms
      for (let i = 0; i < 2; i++) {
        const cur = armCur.current[i];
        const tgt = armTgt.current[i];
        armCur.current[i] = {
          x: lerp(cur.x, tgt.x, alpha),
          y: lerp(cur.y, tgt.y, alpha),
          grip: tgt.grip,
        };
      }

      // Parts held by gripper follow the arm's current animated tip
      for (const t of partsTgt.current) {
        if (t.at.startsWith("gripper_")) {
          const ri = parseInt(t.at.slice(-1), 10) || 0;
          const [x, y] = heldPartXY(armCur.current[ri]);
          t.x = x;
          t.y = y;
        }
      }

      // Lerp parts
      for (const cur of partsCur.current) {
        const tgt = partsTgt.current.find((p) => p.id === cur.id);
        if (!tgt) continue;
        cur.at = tgt.at;
        if (cur.at.startsWith("gripper_")) {
          cur.x = tgt.x;
          cur.y = tgt.y;
          continue;
        }
        cur.x = lerp(cur.x, tgt.x, alpha);
        cur.y = lerp(cur.y, tgt.y, alpha);
      }

      drawScene(
        ctx,
        canvas.width,
        canvas.height,
        armCur.current,
        partsCur.current,
        stepRef.current,
        doneRef.current,
      );
      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      width={520}
      height={300}
      className="w-full h-[300px] rounded-xl"
      style={{ background: "#05080c" }}
    />
  );
}

// ── Main CellView ─────────────────────────────────────────────────────────────

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
  // Live mode: poll latest.png (smoothly updated by MuJoCo sub-step rendering)
  const framePath = liveMujocoFrame
    ? "/sim/latest.png"
    : latest?.frame_url ?? (preferMujocoFrame ? `/sim/replay/step_${replayStep}.png` : undefined);
  const frameSrc = framePath
    ? `${frameBase}${framePath}?t=${frameRefresh}`
    : undefined;
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

  // Fast frame refresh for live MuJoCo mode — 80ms so we catch every sub-step render
  useEffect(() => {
    if (!liveMujocoFrame) return;
    const id = window.setInterval(() => setFrameRefresh((n) => n + 1), 80);
    return () => window.clearInterval(id);
  }, [liveMujocoFrame]);

  useEffect(() => {
    if (!animatedFallback || latest) return;
    const id = window.setInterval(() => setMockTick((n) => n + 1), 650);
    return () => window.clearInterval(id);
  }, [animatedFallback, latest]);

  // Poll sim state for interactive part controls (non-live modes)
  useEffect(() => {
    if (liveMujocoFrame) return; // LiveSmoothCanvas handles its own polling
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
        // MCP server not running
      }
    };
    poll();
    const id = window.setInterval(poll, 500);
    return () => window.clearInterval(id);
  }, [liveMujocoFrame]);

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
        {liveMujocoFrame && <span className="ml-auto pill text-nvidia bg-[rgba(118,185,0,.12)]">Live</span>}
        {showFrame && <span className="ml-auto pill text-nvidia bg-[rgba(118,185,0,.12)]">MuJoCo</span>}
        {!showFrame && !liveMujocoFrame && animatedFallback && <span className="ml-auto pill text-dell-bright bg-[rgba(10,143,220,.14)]">Mock live</span>}
      </h2>

      {showFrame && frameSrc ? (
        <div className="relative">
          <img
            src={frameSrc}
            alt={`MuJoCo sim frame step ${effectiveStep}`}
            className="w-full h-[300px] rounded-xl object-cover border border-line bg-[#05080c]"
            onError={() => setFailedFrameSrc(frameSrc ?? null)}
          />
          <div className="absolute left-3 top-3 rounded-full border border-[rgba(118,185,0,.45)] bg-black/60 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-[1px] text-nvidia-bright">
            {liveMujocoFrame ? "● Live MuJoCo" : "MuJoCo frame"}
          </div>
        </div>
      ) : liveMujocoFrame ? (
        // PNG not available yet — smooth canvas fallback while MuJoCo starts up
        <LiveSmoothCanvas apiBase={SIM_API_BASE} />
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

      {/* Interactive Part Controls — shown in non-live modes when sim state is available */}
      {!liveMujocoFrame && simParts.length > 0 && (
        <div className="mt-3 rounded-xl border border-line/60 p-3 bg-[rgba(255,255,255,.02)]">
          <div className="text-[10px] font-extrabold uppercase tracking-wider text-dim mb-2.5">
            Part Controls — drag to move
          </div>
          <div className="flex gap-3 items-start">
            <div className="flex flex-col gap-1.5 min-w-[110px]">
              {simParts.map((part) => (
                <div
                  key={part.id}
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData("part_id", part.id)}
                  className="flex items-center gap-1.5 px-2 py-1 rounded-lg cursor-grab border border-line/50 bg-[#0e1620] hover:bg-[#111820] select-none"
                  title={`Drag ${part.id} to a zone`}
                >
                  <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: part.color }} />
                  <span className="text-[11px] font-mono text-text">{part.id}</span>
                  <span className="text-[9px] text-dim ml-auto truncate">@{part.at}</span>
                </div>
              ))}
            </div>
            <div className="self-center text-dim text-sm px-1">→</div>
            <div className="grid grid-cols-2 gap-1.5 flex-1">
              {ZONES.map((zone) => {
                const zoneColor =
                  zone === "station_1" || zone === "station_2" ? "#b06bff"
                  : zone === "bin_b" ? "#38b6ff"
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
          {teleporting && <div className="mt-2 text-[10px] text-dim">Moving part…</div>}
        </div>
      )}
    </div>
  );
}
