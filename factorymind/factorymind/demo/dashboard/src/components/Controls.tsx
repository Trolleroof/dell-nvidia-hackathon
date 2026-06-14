import { useRef } from "react";
import type { Mode } from "../types";

interface Props {
  mode: Mode;
  setMode: (m: Mode) => void;
  playing: boolean;
  setPlaying: (p: boolean) => void;
  speed: number;
  setSpeed: (s: number) => void;
  cloud: boolean;
  setCloud: (c: boolean) => void;
  numbersOnly: boolean;
  setNumbersOnly: (n: boolean) => void;
  liveUrl: string;
  setLiveUrl: (u: string) => void;
  hint: string;
  onReset: () => void;
  onLoadReplay: (text: string, name: string) => void;
}

const MODES: { id: Mode; label: string }[] = [
  { id: "mock", label: "Mock Live" },
  { id: "replay", label: "Replay" },
  { id: "live", label: "Live Feed" },
];

export function Controls(p: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => p.onLoadReplay(String(reader.result), file.name);
    reader.readAsText(file);
  };

  return (
    <div className="flex items-center gap-2.5 flex-wrap my-4">
      <div className="inline-flex border border-line rounded-[10px] overflow-hidden bg-panel">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => p.setMode(m.id)}
            className={`px-3.5 py-2 text-[12.5px] font-bold tracking-[0.8px] uppercase border-r border-line last:border-r-0 ${
              p.mode === m.id ? "text-text" : "text-dim"
            }`}
            style={p.mode === m.id ? { background: "linear-gradient(180deg, rgba(255,255,255,.08), transparent)" } : undefined}
          >
            {m.label}
          </button>
        ))}
      </div>

      <button
        className="btn"
        style={{
          background: "linear-gradient(180deg, rgba(118,185,0,.25), rgba(118,185,0,.08))",
          borderColor: "rgba(118,185,0,.5)",
          color: "#95e600",
        }}
        onClick={() => p.setPlaying(!p.playing)}
      >
        {p.playing ? "⏸ Pause" : "▶ Play"}
      </button>
      <button className="btn bg-transparent" onClick={p.onReset}>↺ Reset</button>

      <span className="inline-flex items-center gap-2 text-xs font-bold text-dim">
        Speed
        <input
          type="range"
          min={0.25}
          max={4}
          step={0.25}
          value={p.speed}
          onChange={(e) => p.setSpeed(parseFloat(e.target.value))}
          className="w-[120px] accent-nvidia"
        />
        <span>{p.speed.toFixed(2).replace(/0$/, "")}×</span>
      </span>

      <label
        className={`inline-flex items-center gap-2 text-[12.5px] font-bold tracking-[0.6px] uppercase border rounded-[10px] px-3 py-1.5 cursor-pointer select-none bg-panel ${
          p.cloud ? "text-cloud border-[rgba(176,107,255,.5)]" : "text-dim border-line"
        }`}
      >
        <input type="checkbox" checked={p.cloud} onChange={(e) => p.setCloud(e.target.checked)} className="w-[15px] h-[15px] accent-cloud" />
        Show Cloud (simulated)
      </label>

      <label className="inline-flex items-center gap-2 text-[12.5px] font-bold tracking-[0.6px] uppercase border border-line rounded-[10px] px-3 py-1.5 cursor-pointer select-none bg-panel text-dim">
        <input type="checkbox" checked={p.numbersOnly} onChange={(e) => p.setNumbersOnly(e.target.checked)} className="w-[15px] h-[15px]" />
        Numbers only
      </label>

      {p.mode === "replay" && (
        <>
          <input ref={fileRef} type="file" accept=".jsonl,.json,.txt" className="hidden" onChange={onFile} />
          <button className="btn" onClick={() => fileRef.current?.click()}>📂 Load .jsonl</button>
        </>
      )}
      {p.mode === "live" && (
        <input
          value={p.liveUrl}
          onChange={(e) => p.setLiveUrl(e.target.value)}
          className="btn normal-case w-[260px] text-left"
          spellCheck={false}
        />
      )}

      <span className="text-[11.5px] text-faint">{p.hint}</span>
    </div>
  );
}
