import type { TelemetryRow } from "../types";
import { isAR } from "../types";
import { fmt } from "../lib/stats";

function statusPill(row: TelemetryRow) {
  if (!row.parsed_ok) return <span className="pill text-danger bg-[rgba(255,84,112,.14)]">parse fail</span>;
  if (row.retries) return <span className="pill text-warn bg-[rgba(255,176,46,.14)]">retry {row.retries}</span>;
  return <span className="pill text-nvidia bg-[rgba(118,185,0,.12)]">parsed</span>;
}

export function ActionStream({ rows }: { rows: TelemetryRow[] }) {
  return (
    <div className="card">
      <h2 className="card-title"><span className="tick" />Parsed Action Stream</h2>
      <div className="max-h-[320px] overflow-y-auto flex flex-col gap-[7px] pr-1">
        {rows.map((row, i) => {
          const ar = isAR(row.model);
          return (
            <div
              key={`${row.step}-${row.model}-${i}`}
              className="rounded-lg border border-lineSoft border-l-[3px] px-[11px] py-2 bg-panel2 animate-slidein"
              style={{ borderLeftColor: ar ? "#0a8fdc" : "#76b900" }}
            >
              <div className="flex items-center gap-2 text-[11px]">
                <span className="font-extrabold tracking-[0.5px] uppercase text-[10.5px]" style={{ color: ar ? "#38b6ff" : "#95e600" }}>
                  {ar ? "Gemma4" : "Diffusion"}
                </span>
                <span className="text-faint font-mono">step {row.step}</span>
                <span className="ml-auto text-dim tabular-nums">{fmt(row.latency_ms)} ms</span>
              </div>
              <div className="text-[13px] mt-1 font-mono">{row.action_summary}</div>
              <div className="text-[11px] mt-1 flex items-center gap-1.5">
                {statusPill(row)}
                {row.sim_event && (
                  <span className={`pill ${row.sim_event === "collision" ? "text-danger bg-[rgba(255,84,112,.14)]" : "text-dell-bright bg-[rgba(10,143,220,.14)]"}`}>
                    {row.sim_event}
                  </span>
                )}
                <span className="text-faint">· {fmt(row._tokS ?? 0)} tok/s · ttft {fmt(row.ttft_ms)}ms</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
