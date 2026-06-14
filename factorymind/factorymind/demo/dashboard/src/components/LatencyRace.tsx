import type { TelemetryRow } from "../types";
import { fmt } from "../lib/stats";

function Lane({ row, kind }: { row?: TelemetryRow; kind: "diffusion" | "ar" }) {
  const isD = kind === "diffusion";
  const name = isD ? "DiffusionGemma" : "Gemma 4 (AR)";
  const tag = isD ? "Hero · Parallel" : "Baseline · Sequential";
  const endpoint = isD ? ":8000 /v1 · NVFP4" : ":8001 /v1 · BF16";
  const accent = isD ? "#95e600" : "#38b6ff";
  const border = isD ? "rgba(118,185,0,.35)" : "rgba(10,143,220,.35)";
  const glow = isD ? "rgba(118,185,0,.06)" : "rgba(10,143,220,.06)";

  return (
    <div
      className="rounded-[14px] border p-4 relative overflow-hidden bg-panel"
      style={{ borderColor: border, boxShadow: `inset 0 0 40px ${glow}` }}
    >
      <div className="flex items-baseline gap-2.5">
        <span className="text-[17px] font-extrabold" style={{ color: accent }}>{name}</span>
        <span className="text-[10.5px] font-extrabold tracking-[1.5px] uppercase text-faint">{tag}</span>
      </div>
      <div className="text-[11px] text-faint mt-0.5 font-mono">{endpoint}</div>

      <div className="mt-2.5 flex items-end gap-2">
        <span className="text-[58px] leading-[0.92] font-extrabold tabular-nums" style={{ color: accent }}>
          {row ? fmt(row._tokS ?? 0) : "0"}
        </span>
        <span className="text-sm text-dim font-bold pb-[7px]">tok/s</span>
      </div>

      <div className="grid grid-cols-2 gap-2.5 mt-3.5">
        <div className="stat">
          <div className="stat-k">Total / decision</div>
          <div className="text-[22px] font-extrabold tabular-nums mt-0.5">
            {row ? fmt(row.latency_ms) : 0}
            <small className="text-xs text-dim font-semibold"> ms</small>
          </div>
        </div>
        <div className="stat">
          <div className="stat-k">TTFT</div>
          <div className="text-[22px] font-extrabold tabular-nums mt-0.5">
            {row ? fmt(row.ttft_ms) : 0}
            <small className="text-xs text-dim font-semibold"> ms</small>
          </div>
        </div>
      </div>

      <div className="flex justify-between text-[11px] text-faint mt-3">
        <span>decision {row?.step ?? "—"}</span>
        <span>{row ? fmt(row.completion_tokens) : 0} tok</span>
      </div>
    </div>
  );
}

export function LatencyRace({ d, a }: { d?: TelemetryRow; a?: TelemetryRow }) {
  return (
    <div className="card">
      <h2 className="card-title"><span className="tick" />Latency Race · Per Control Decision</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        <Lane row={d} kind="diffusion" />
        <Lane row={a} kind="ar" />
      </div>
    </div>
  );
}
