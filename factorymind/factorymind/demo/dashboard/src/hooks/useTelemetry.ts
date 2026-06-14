import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TelemetryRow } from "../types";
import { isAR } from "../types";
import { aggregate, parseJSONL, withTokS } from "../lib/stats";

const MAX_PTS = 60;
const MAX_STREAM = 40;

export interface ChartPoint {
  step: number;
  diffusion?: number;
  ar?: number;
}

export function useTelemetry() {
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [liveUrl, setLiveUrl] = useState("../../telemetry/run.jsonl");
  const [hint, setHint] = useState("Live — polling sim feed on :8766.");

  const dRowsRef = useRef<TelemetryRow[]>([]);
  const aRowsRef = useRef<TelemetryRow[]>([]);
  const [, force] = useState(0);
  const rerender = useCallback(() => force((n) => n + 1), []);

  const [latest, setLatest] = useState<{ d?: TelemetryRow; a?: TelemetryRow }>({});
  const [stream, setStream] = useState<TelemetryRow[]>([]);
  const [throughput, setThroughput] = useState<ChartPoint[]>([]);
  const [latency, setLatency] = useState<ChartPoint[]>([]);
  const [step, setStep] = useState(0);

  const ingest = useCallback(
    (d?: TelemetryRow, a?: TelemetryRow) => {
      const dn = d ? withTokS(d) : undefined;
      const an = a ? withTokS(a) : undefined;
      const curStep = dn?.step ?? an?.step ?? 0;

      if (dn) dRowsRef.current.push(dn);
      if (an) aRowsRef.current.push(an);

      setLatest({ d: dn, a: an });
      setStep((s) => Math.max(s, curStep));
      setStream((prev) => [an, dn].filter(Boolean).concat(prev).slice(0, MAX_STREAM) as TelemetryRow[]);
      setThroughput((prev) => [...prev, { step: curStep, diffusion: dn?._tokS, ar: an?._tokS }].slice(-MAX_PTS));
      setLatency((prev) =>
        [...prev, { step: curStep, diffusion: dn?.latency_ms, ar: an?.latency_ms }].slice(-MAX_PTS),
      );
      rerender();
    },
    [rerender],
  );

  const reset = useCallback(() => {
    dRowsRef.current = [];
    aRowsRef.current = [];
    setLatest({});
    setStream([]);
    setThroughput([]);
    setLatency([]);
    setStep(0);
    rerender();
  }, [rerender]);

  // ----- LIVE (only mode): poll JSONL, tail new rows -----
  const seenRef = useRef(0);
  useEffect(() => {
    if (!playing) return;
    seenRef.current = 0;
    reset();
    const poll = async () => {
      try {
        const res = await fetch(liveUrl, { cache: "no-store" });
        if (!res.ok) throw new Error(String(res.status));
        const rows = parseJSONL(await res.text());
        const fresh = rows.slice(seenRef.current);
        seenRef.current = rows.length;
        const byStep = new Map<number, TelemetryRow[]>();
        fresh.forEach((row) => {
          const arr = byStep.get(row.step) ?? [];
          arr.push(row);
          byStep.set(row.step, arr);
        });
        [...byStep.keys()].sort((x, y) => x - y).forEach((s) => {
          let d: TelemetryRow | undefined;
          let a: TelemetryRow | undefined;
          byStep.get(s)!.forEach((row) => (isAR(row.model) ? (a = row) : (d = row)));
          ingest(d, a);
        });
        setHint(`Live · ${liveUrl} · ${seenRef.current} rows seen`);
      } catch (e) {
        setHint(`Live feed unreachable (${(e as Error).message}) — serve over http, point at B's JSONL.`);
      }
    };
    poll();
    const id = setInterval(poll, 300);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, liveUrl, ingest]);

  const aggregates = useMemo(
    () => ({ d: aggregate(dRowsRef.current), a: aggregate(aRowsRef.current) }),
    // recompute whenever step or stream changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [step, stream],
  );

  return {
    playing, setPlaying,
    speed, setSpeed,
    liveUrl, setLiveUrl,
    hint,
    latest, stream, throughput, latency, step,
    aggregates,
    diffusionRows: dRowsRef.current,
    arRows: aRowsRef.current,
    reset,
  };
}
