import type { Aggregate, TelemetryRow } from "../types";

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

// Derive tokens/sec for the generation phase if a row didn't ship with it
// (replay / live files won't include the client-side _tokS field).
export function withTokS(row: TelemetryRow): TelemetryRow {
  if (row._tokS != null) return row;
  const gen = Math.max(1, row.latency_ms - row.ttft_ms);
  return { ...row, _tokS: row.completion_tokens / (gen / 1000) };
}

export function aggregate(rows: TelemetryRow[]): Aggregate | null {
  if (!rows.length) return null;
  const totals = rows.map((r) => r.latency_ms).slice().sort((a, b) => a - b);
  const mean = (arr: number[]) => arr.reduce((s, v) => s + v, 0) / arr.length;
  const pct = (arr: number[], p: number) =>
    arr[clamp(Math.floor((p / 100) * arr.length), 0, arr.length - 1)];
  return {
    n: rows.length,
    meanTokS: mean(rows.map((r) => r._tokS ?? 0)),
    meanTotal: mean(totals),
    p50: pct(totals, 50),
    p95: pct(totals, 95),
    meanTtft: mean(rows.map((r) => r.ttft_ms)),
    parsePct: (rows.filter((r) => r.parsed_ok).length / rows.length) * 100,
    tokSum: rows.reduce((s, r) => s + r.completion_tokens, 0),
  };
}

export const fmt = (n: number, d = 0) =>
  Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });

export function parseJSONL(text: string): TelemetryRow[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      try {
        return JSON.parse(l) as TelemetryRow;
      } catch {
        return null;
      }
    })
    .filter((r): r is TelemetryRow => r != null)
    .map(withTokS);
}
