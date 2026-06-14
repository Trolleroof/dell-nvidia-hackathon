import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Mode, TelemetryRow } from "../types";
import { isAR } from "../types";
import { decisionPair } from "../lib/mockEngine";
import { aggregate, ISOLATED_REPLAY_PATHS, mergeIsolatedRuns, parseJSONL, withTokS } from "../lib/stats";

const MAX_PTS = 60;
const MAX_STREAM = 40;

export interface ChartPoint {
  step: number;
  diffusion?: number;
  ar?: number;
  cloud?: number;
}

export interface TelemetryState {
  mode: Mode;
  playing: boolean;
  speed: number;
  cloud: boolean;
  step: number;
  latest: { d?: TelemetryRow; a?: TelemetryRow };
  stream: TelemetryRow[];
  throughput: ChartPoint[];
  latency: ChartPoint[];
  cloudRtt: number;
  diffusionRows: TelemetryRow[];
  arRows: TelemetryRow[];
  hint: string;
}

const rnd = (a: number, b: number) => a + Math.random() * (b - a);

export function useTelemetry() {
  const [mode, setMode] = useState<Mode>("mock");
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [cloud, setCloud] = useState(true);
  const [liveUrl, setLiveUrl] = useState("../../telemetry/run.jsonl");
  const [hint, setHint] = useState("Synthetic fast/slow timings — rehearse with no GPU.");

  const dRowsRef = useRef<TelemetryRow[]>([]);
  const aRowsRef = useRef<TelemetryRow[]>([]);
  const [, force] = useState(0);
  const rerender = useCallback(() => force((n) => n + 1), []);

  const [latest, setLatest] = useState<{ d?: TelemetryRow; a?: TelemetryRow }>({});
  const [stream, setStream] = useState<TelemetryRow[]>([]);
  const [throughput, setThroughput] = useState<ChartPoint[]>([]);
  const [latency, setLatency] = useState<ChartPoint[]>([]);
  const [cloudRtt, setCloudRtt] = useState(0);
  const [step, setStep] = useState(0);

  const cloudRef = useRef(cloud);
  cloudRef.current = cloud;

  const ingest = useCallback((d?: TelemetryRow, a?: TelemetryRow) => {
    const dn = d ? withTokS(d) : undefined;
    const an = a ? withTokS(a) : undefined;
    const curStep = dn?.step ?? an?.step ?? 0;

    if (dn) dRowsRef.current.push(dn);
    if (an) aRowsRef.current.push(an);

    setLatest({ d: dn, a: an });
    setStep((s) => Math.max(s, curStep));
    setStream((prev) => [an, dn].filter(Boolean).concat(prev).slice(0, MAX_STREAM) as TelemetryRow[]);

    const rtt = cloudRef.current ? rnd(120, 280) : 0;
    if (cloudRef.current) setCloudRtt(rtt);

    setThroughput((prev) =>
      [...prev, { step: curStep, diffusion: dn?._tokS, ar: an?._tokS }].slice(-MAX_PTS),
    );
    setLatency((prev) =>
      [
        ...prev,
        {
          step: curStep,
          diffusion: dn?.latency_ms,
          ar: an?.latency_ms,
          cloud: cloudRef.current && an ? an.latency_ms + rtt : undefined,
        },
      ].slice(-MAX_PTS),
    );
    rerender();
  }, [rerender]);

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

  // ----- MOCK mode -----
  const stepRef = useRef(0);
  useEffect(() => {
    if (mode !== "mock" || !playing) return;
    const id = setInterval(() => {
      stepRef.current += 1;
      const [d, a] = decisionPair(stepRef.current, Date.now() / 1000);
      ingest(d, a);
    }, 1100 / speed);
    return () => clearInterval(id);
  }, [mode, playing, speed, ingest]);

  useEffect(() => {
    if (mode === "mock") {
      reset();
      stepRef.current = 0;
      setHint("Synthetic fast/slow timings — rehearse with no GPU.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // ----- REPLAY mode -----
  const replayRef = useRef<{ rows: TelemetryRow[]; idx: number }>({ rows: [], idx: 0 });
  const loadReplay = useCallback(
    (text: string, name: string) => {
      const rows = parseJSONL(text).sort(
        (x, y) => x.step - y.step || (isAR(x.model) ? 1 : 0) - (isAR(y.model) ? 1 : 0),
      );
      replayRef.current = { rows, idx: 0 };
      reset();
      setMode("replay");
      setPlaying(true);
      setHint(`Loaded ${name} · ${rows.length} rows — replaying.`);
    },
    [reset],
  );

  const loadIsolatedReplay = useCallback(
    (diffusionText: string, arText: string, label = "isolated runs") => {
      const rows = mergeIsolatedRuns(parseJSONL(diffusionText), parseJSONL(arText));
      replayRef.current = { rows, idx: 0 };
      reset();
      setMode("replay");
      setPlaying(true);
      setHint(
        `Loaded ${label} · ${rows.length} rows (${rows.filter((r) => !isAR(r.model)).length} diffusion + ${rows.filter((r) => isAR(r.model)).length} AR) — replaying side-by-side.`,
      );
    },
    [reset],
  );

  const fetchIsolatedReplay = useCallback(async () => {
    try {
      const [dRes, aRes] = await Promise.all([
        fetch(ISOLATED_REPLAY_PATHS.diffusion, { cache: "no-store" }),
        fetch(ISOLATED_REPLAY_PATHS.ar, { cache: "no-store" }),
      ]);
      if (!dRes.ok || !aRes.ok) throw new Error(`${dRes.status}/${aRes.status}`);
      loadIsolatedReplay(await dRes.text(), await aRes.text(), "diffusion_run + ar_run");
    } catch (e) {
      setHint(`Isolated replay unreachable (${(e as Error).message}) — run run_team_feed first, serve over http.`);
    }
  }, [loadIsolatedReplay]);

  useEffect(() => {
    if (mode !== "replay" || !playing) return;
    const id = setInterval(() => {
      const r = replayRef.current;
      if (r.idx >= r.rows.length) {
        setHint(`Replay finished — ${r.rows.length} rows.`);
        clearInterval(id);
        return;
      }
      const curStep = r.rows[r.idx].step;
      let d: TelemetryRow | undefined;
      let a: TelemetryRow | undefined;
      while (r.idx < r.rows.length && r.rows[r.idx].step === curStep) {
        const row = r.rows[r.idx++];
        if (isAR(row.model)) a = row;
        else d = row;
      }
      ingest(d, a);
    }, 1000 / speed);
    return () => clearInterval(id);
  }, [mode, playing, speed, ingest]);

  // ----- LIVE mode (poll JSONL, tail new rows) -----
  const seenRef = useRef(0);
  useEffect(() => {
    if (mode !== "live" || !playing) return;
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
  }, [mode, playing, liveUrl, ingest]);

  const aggregates = useMemo(
    () => ({ d: aggregate(dRowsRef.current), a: aggregate(aRowsRef.current) }),
    // recompute whenever step or stream changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [step, stream],
  );

  return {
    mode, setMode,
    playing, setPlaying,
    speed, setSpeed,
    cloud, setCloud,
    liveUrl, setLiveUrl,
    hint,
    latest, stream, throughput, latency, cloudRtt, step,
    aggregates,
    diffusionRows: dRowsRef.current,
    arRows: aRowsRef.current,
    reset, loadReplay, loadIsolatedReplay, fetchIsolatedReplay,
  };
}
