import type { Aggregate } from "../types";
import { fmt } from "../lib/stats";

export function WinnerBanner({ d, a, cloud }: { d: Aggregate | null; a: Aggregate | null; cloud: boolean }) {
  const tokRatio = d && a ? d.meanTokS / a.meanTokS : null;
  const e2eRatio = d && a ? a.meanTotal / d.meanTotal : null;
  return (
    <div
      className="mt-4 border border-line rounded-[14px] px-4 py-3.5 flex items-center gap-4"
      style={{
        background: cloud
          ? "linear-gradient(90deg, rgba(118,185,0,.10), rgba(176,107,255,.10))"
          : "linear-gradient(90deg, rgba(118,185,0,.10), rgba(10,143,220,.06))",
      }}
    >
      <div>
        <div className="text-3xl font-extrabold tabular-nums text-nvidia-bright">
          {tokRatio ? `${fmt(tokRatio, 2)}×` : "—"}
        </div>
        <div className="text-[11px] tracking-[1px] uppercase text-dim">tokens/sec · diffusion vs AR</div>
      </div>
      <div className="w-px self-stretch bg-line" />
      <div>
        <div className="text-3xl font-extrabold tabular-nums text-nvidia-bright">
          {e2eRatio ? `${fmt(e2eRatio, 2)}×` : "—"}
        </div>
        <div className="text-[11px] tracking-[1px] uppercase text-dim">end-to-end on long outputs</div>
      </div>
      <div className="w-px self-stretch bg-line" />
      <div className="text-[11.5px] text-faint max-w-[340px] leading-snug">
        Diffusion's TTFT is <b>higher by design</b> (reported separately). The win is{" "}
        <b>throughput on long, structured action blocks</b> — parallel generation for parallel control.
      </div>
    </div>
  );
}
