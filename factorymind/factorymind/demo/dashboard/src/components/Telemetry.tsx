import type { TelemetryRow } from "../types";
import { isAR } from "../types";

function fmtMs(ms?: number): string {
  if (ms == null) return "—";
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${Math.round(ms)}ms`;
}

// ── Tier 1: wall-clock latency, Diffusion vs AR ───────────────────────────────
export function MetricsPanel({ d, a }: { d?: TelemetryRow; a?: TelemetryRow }) {
  const dl = d?.latency_ms;
  const al = a?.latency_ms;
  // Bars show WALL-CLOCK ms — lower (shorter) is faster. Honest metric, not tok/s.
  const maxL = Math.max(dl ?? 0, al ?? 0, 1);
  const faster = dl != null && al != null ? (dl <= al ? "d" : "a") : null;
  const speedup = dl && al ? (al / dl).toFixed(2) : null;

  return (
    <div className="card">
      <h2 className="card-title">
        <span className="tick" />
        Latency · Diffusion vs AR
        <span className="ml-auto inline-block border border-dell-bright px-2 py-px font-mono text-[9px] font-bold uppercase tracking-[0.14em] text-dell-bright">
          Model estimate
        </span>
      </h2>
      <p className="-mt-2 mb-4 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
        Wall-clock per decision · lower = faster · projected on-device (nvfp4)
      </p>

      {/* Headline — both numbers side by side, no empty bar */}
      <div className="flex items-end gap-4 border-b border-border-light pb-4">
        <div>
          <div className="font-display text-4xl font-extrabold tabular-nums leading-none text-nvidia-bright">{fmtMs(dl)}</div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-foreground">Diffusion · est.</div>
        </div>
        <div className="pb-0.5 font-mono text-2xl text-muted-foreground">vs</div>
        <div>
          <div className="font-display text-4xl font-extrabold tabular-nums leading-none text-dell-bright">{fmtMs(al)}</div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">AR · Gemma · est.</div>
        </div>
        {speedup && (
          <div className="ml-auto pb-0.5 text-right">
            <div className="font-display text-xl font-extrabold tabular-nums text-nvidia-bright">{speedup}×</div>
            <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">faster</div>
          </div>
        )}
      </div>

      {/* ms race bars — lower = faster */}
      <div className="mt-4">
        <Bar label="Diffusion" value={dl} pct={dl != null ? (dl / maxL) * 100 : 0} color="var(--nv-bright)" win={faster === "d"} />
        <Bar label="AR · Gemma" value={al} pct={al != null ? (al / maxL) * 100 : 0} color="var(--dell-bright)" win={faster === "a"} />
      </div>
    </div>
  );
}

function Bar({
  label,
  value,
  pct,
  color,
  win,
}: {
  label: string;
  value?: number;
  pct: number;
  color: string;
  win: boolean;
}) {
  return (
    <div className="mb-2.5 last:mb-0">
      <div className="mb-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.1em]">
        <span className="text-foreground">{label}</span>
        {win && <span style={{ color }}>▲ faster</span>}
        <span className="ml-auto tabular-nums text-muted-foreground">{fmtMs(value)}</span>
      </div>
      <div className="h-2 w-full border border-border-light bg-[var(--muted)]">
        <div className="h-full transition-all duration-200" style={{ width: `${Math.max(6, pct)}%`, background: color }} />
      </div>
    </div>
  );
}

// ── Tier 2: live decision / event stream ──────────────────────────────────────
function eventClass(e?: string): string {
  const base = "shrink-0 font-mono text-[9px] font-semibold uppercase tracking-[0.12em]";
  if (!e) return `${base} text-faint`;
  if (e.includes("success") || e === "task_complete") return `${base} text-nvidia-bright`;
  if (e.includes("collision") || e.includes("error") || e.includes("miss")) return `${base} text-dell-bright`;
  return `${base} text-muted-foreground`;
}

export function ActivityLog({ stream }: { stream: TelemetryRow[] }) {
  // One entry per step (diffusion series), newest first.
  const rows = stream.filter((r) => !isAR(r.model)).slice(0, 14);
  return (
    <div className="card">
      <h2 className="card-title">
        <span className="tick" />
        Activity Log
      </h2>
      <p className="-mt-2 mb-3 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
        Live agent decisions &amp; sim events · newest first
      </p>
      <div className="flex max-h-[220px] flex-col gap-1.5 overflow-y-auto">
        {rows.length === 0 && (
          <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-faint">Awaiting decisions…</div>
        )}
        {rows.map((r, i) => (
          <div
            key={`${r.step}-${i}`}
            className={`grid grid-cols-[auto_1fr_auto] items-center gap-3 border-b border-border-light pb-1.5 font-mono text-[11px] ${i === 0 ? "animate-slidein" : ""}`}
          >
            <span className="tabular-nums text-muted-foreground">#{String(r.step).padStart(2, "0")}</span>
            <span className="truncate text-foreground">{r.action_summary}</span>
            <span className={eventClass(r.sim_event)}>{r.sim_event}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
