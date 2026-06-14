import type { Aggregate } from "../types";
import { fmt } from "../lib/stats";

function Cell({ k, v, unit, color }: { k: string; v: string; unit?: string; color?: string }) {
  return (
    <div className="stat">
      <div className="stat-k">{k}</div>
      <div className="stat-v" style={color ? { color } : undefined}>
        {v}
        {unit && <small className="text-xs text-dim font-semibold"> {unit}</small>}
      </div>
    </div>
  );
}

function AggCard({ title, agg, accent, tickColor }: { title: string; agg: Aggregate | null; accent: string; tickColor: string }) {
  return (
    <div className="card">
      <h2 className="card-title">
        <span className="tick" style={{ background: tickColor, boxShadow: `0 0 12px ${tickColor}` }} />
        {title}
      </h2>
      <div className="grid grid-cols-2 gap-2.5">
        <Cell k="Mean tok/s" v={fmt(agg?.meanTokS ?? 0)} color={accent} />
        <Cell k="Mean total" v={fmt(agg?.meanTotal ?? 0)} unit="ms" color={accent} />
        <Cell k="p50 total" v={fmt(agg?.p50 ?? 0)} unit="ms" />
        <Cell k="p95 total" v={fmt(agg?.p95 ?? 0)} unit="ms" />
        <Cell k="Mean TTFT" v={fmt(agg?.meanTtft ?? 0)} unit="ms" />
        <Cell k="Parse OK" v={fmt(agg?.parsePct ?? 100)} unit="%" />
      </div>
    </div>
  );
}

interface Props {
  d: Aggregate | null;
  a: Aggregate | null;
  cloud: boolean;
  cloudRtt: number;
  step: number;
  decisions: number;
}

export function StatsPanel({ d, a, cloud, cloudRtt, step, decisions }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <AggCard title="DiffusionGemma · Aggregate" agg={d} accent="#95e600" tickColor="#76b900" />
      <AggCard title="Gemma 4 AR · Aggregate" agg={a} accent="#38b6ff" tickColor="#0a8fdc" />

      {cloud && (
        <div className="card">
          <h2 className="card-title">
            <span className="tick" style={{ background: "#b06bff", boxShadow: "0 0 12px #b06bff" }} />
            Cloud (Simulated)
          </h2>
          <div className="grid grid-cols-1 gap-2.5">
            <Cell k="+ Network round-trip / decision" v={fmt(cloudRtt)} unit="ms" color="#b06bff" />
            <div className="stat">
              <div className="stat-k">Why it's a non-starter</div>
              <div className="text-xs text-dim leading-relaxed mt-1">
                A real-time control loop can't wait on a round-trip every decision — and cell data can't leave the
                floor. <b className="text-cloud">FactoryMind runs fully local.</b>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="card-title"><span className="tick" />Run Summary</h2>
        <div className="grid grid-cols-2 gap-2.5">
          <Cell k="Decisions" v={fmt(decisions)} />
          <Cell k="Sim step" v={fmt(step)} />
          <div className="stat col-span-2">
            <div className="stat-k">Tokens generated (D / AR)</div>
            <div className="stat-v">
              <span className="text-nvidia-bright">{fmt(d?.tokSum ?? 0)}</span>
              <small className="text-dim"> / </small>
              <span className="text-dell-bright">{fmt(a?.tokSum ?? 0)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
