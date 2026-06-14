import { useState } from "react";
import { useTelemetry } from "./hooks/useTelemetry";
import { Header } from "./components/Header";
import { Controls } from "./components/Controls";
import { CellView } from "./components/CellView";
import { ActionStream } from "./components/ActionStream";
import { LatencyRace } from "./components/LatencyRace";
import { WinnerBanner } from "./components/WinnerBanner";
import { ThroughputChart, LatencyChart } from "./components/Charts";
import { StatsPanel } from "./components/StatsPanel";

export default function App() {
  const t = useTelemetry();
  const [numbersOnly, setNumbersOnly] = useState(false);
  const [resetKey, setResetKey] = useState(0);

  const onReset = () => {
    t.reset();
    setResetKey((k) => k + 1);
  };

  return (
    <div className="relative z-[1] max-w-[1920px] mx-auto px-[22px] pt-[18px] pb-7">
      <Header mode={t.mode} />

      <Controls
        mode={t.mode}
        setMode={t.setMode}
        playing={t.playing}
        setPlaying={t.setPlaying}
        speed={t.speed}
        setSpeed={t.setSpeed}
        cloud={t.cloud}
        setCloud={t.setCloud}
        numbersOnly={numbersOnly}
        setNumbersOnly={setNumbersOnly}
        liveUrl={t.liveUrl}
        setLiveUrl={t.setLiveUrl}
        hint={t.hint}
        onReset={onReset}
        onLoadReplay={t.loadReplay}
        onFetchIsolatedReplay={t.fetchIsolatedReplay}
      />

      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2 2xl:grid-cols-[1.05fr_1.55fr_0.95fr]">
        {/* LEFT: cell + action stream */}
        {!numbersOnly && (
          <div className="flex flex-col gap-4">
            <CellView latest={t.latest.d ?? t.latest.a} step={t.step} resetKey={resetKey} />
            <ActionStream rows={t.stream} />
          </div>
        )}
        {numbersOnly && <ActionStream rows={t.stream} />}

        {/* CENTER: the race + charts */}
        <div className="flex flex-col gap-4">
          <div>
            <LatencyRace d={t.latest.d} a={t.latest.a} />
            <WinnerBanner d={t.aggregates.d} a={t.aggregates.a} cloud={t.cloud} />
          </div>
          <ThroughputChart data={t.throughput} />
          <LatencyChart data={t.latency} cloud={t.cloud} />
        </div>

        {/* RIGHT: aggregate stats */}
        <StatsPanel
          d={t.aggregates.d}
          a={t.aggregates.a}
          cloud={t.cloud}
          cloudRtt={t.cloudRtt}
          step={t.step}
          decisions={t.diffusionRows.length}
        />
      </div>

      <div className="mt-[22px] flex items-center gap-2.5 text-[11.5px] text-faint flex-wrap">
        <span>FactoryMind · Role C dashboard</span>
        <span className="w-1 h-1 rounded-full bg-faint" />
        <span>C5 telemetry schema</span>
        <span className="w-1 h-1 rounded-full bg-faint" />
        <span>React · Vite · Tailwind · Recharts</span>
        <span className="w-1 h-1 rounded-full bg-faint" />
        <span>{t.mode}</span>
      </div>
    </div>
  );
}
