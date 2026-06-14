import type { TelemetryRow } from "../types";

// Synthetic C5 telemetry generator — mirrors gen_mock_telemetry.py so the
// dashboard can be rehearsed with no GPU. Honest framing: diffusion has HIGHER
// TTFT but HIGHER tok/s on long outputs; AR has low TTFT, lower throughput, and
// occasional stutter.

const TARGETS = ["bin_a", "bin_b", "station_1", "station_2", "part_1", "part_2", "part_3"];
const ACTIONS = ["move", "grip", "release", "hold"];
const EVENTS = ["pick_success", "place_success", "task_progress", "handoff", "collision"];

const rnd = (a: number, b: number) => a + Math.random() * (b - a);
const pick = <T,>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)];

function actionSummary(): string {
  return `r0 ${pick(ACTIONS)} ${pick(TARGETS)}; r1 ${pick(ACTIONS)} ${pick(TARGETS)}`;
}

export function decisionPair(step: number, ts: number): [TelemetryRow, TelemetryRow] {
  const completion = Math.round(rnd(200, 260)); // identical max-tokens => fair race
  const prompt = Math.round(rnd(420, 520));
  const summary = actionSummary();
  const event = pick(EVENTS);

  let dTokS = rnd(98, 124);
  const dTtft = rnd(190, 250);
  let dParsed = true;
  let dRetries = 0;
  if (Math.random() < 0.06) {
    dParsed = false;
    dRetries = 1;
    dTokS *= 0.82;
  }
  const dTotal = dTtft + (completion / dTokS) * 1000;

  let aTokS = rnd(52, 66);
  const aTtft = rnd(45, 80);
  if (Math.random() < 0.1) aTokS *= rnd(0.45, 0.7);
  const aTotal = aTtft + (completion / aTokS) * 1000;

  const base = {
    step,
    prompt_tokens: prompt,
    completion_tokens: completion,
    action_summary: summary,
    sim_event: event,
  };

  return [
    {
      ts,
      model: "diffusiongemma",
      endpoint: "http://localhost:8000/v1",
      latency_ms: Math.round(dTotal),
      ttft_ms: Math.round(dTtft),
      parsed_ok: dParsed,
      retries: dRetries,
      _tokS: dTokS,
      ...base,
    },
    {
      ts: ts + 0.001,
      model: "gemma4",
      endpoint: "http://localhost:8001/v1",
      latency_ms: Math.round(aTotal),
      ttft_ms: Math.round(aTtft),
      parsed_ok: true,
      retries: 0,
      _tokS: aTokS,
      ...base,
    },
  ];
}
