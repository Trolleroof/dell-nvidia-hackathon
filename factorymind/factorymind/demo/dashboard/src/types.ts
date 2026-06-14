// C5 — Telemetry JSONL schema (frozen contract, owned by Role B, consumed by C).
// One line per model per control step.

export type ModelName = "diffusiongemma" | "gemma4" | "mock" | "oracle";

export interface TelemetryRow {
  ts: number;
  step: number;
  model: ModelName;
  endpoint: string;
  precision?: "nvfp4" | "bf16";
  latency_ms: number;
  ttft_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  parsed_ok: boolean;
  retries: number;
  action_summary: string;
  sim_event: string;
  frame_url?: string;
  // derived client-side (not in the file), tokens/sec for the generation phase:
  _tokS?: number;
}

export interface Aggregate {
  n: number;
  meanTokS: number;
  meanTotal: number;
  p50: number;
  p95: number;
  meanTtft: number;
  parsePct: number;
  tokSum: number;
}

export type Mode = "mock" | "replay" | "live";

export const isAR = (m: ModelName): boolean => m === "gemma4";
export const isDiffusion = (m: ModelName): boolean => m === "diffusiongemma";
