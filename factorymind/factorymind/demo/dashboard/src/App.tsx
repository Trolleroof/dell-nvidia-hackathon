import { useEffect, useState } from "react";
import { ActionStream } from "./components/ActionStream";
import { AgentSimPage } from "./components/AgentSimPage";
import { ThroughputChart, LatencyChart } from "./components/Charts";
import { CellView } from "./components/CellView";
import { Controls } from "./components/Controls";
import { Header } from "./components/Header";
import { LatencyRace } from "./components/LatencyRace";
import { StatsPanel } from "./components/StatsPanel";
import { WinnerBanner } from "./components/WinnerBanner";
import { useTelemetry } from "./hooks/useTelemetry";
import type { Mode } from "./types";

function getRoute() {
  return window.location.hash === "#/agent" ? "/agent" : "/";
}

function labelForMode(mode: Mode) {
  if (mode === "mock") return "Mock";
  if (mode === "replay") return "Replay";
  return "Live Feed";
}

function NavLink({ href, active, label }: { href: string; active: boolean; label: string }) {
  return (
    <a
      href={href}
      className={`border px-3 py-2 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] ${
        active ? "border-foreground bg-foreground text-background" : "border-border-light text-muted-foreground"
      }`}
    >
      {label}
    </a>
  );
}

export default function App() {
  const t = useTelemetry();
  const [resetKey, setResetKey] = useState(0);
  const [numbersOnly, setNumbersOnly] = useState(false);
  const [route, setRoute] = useState(getRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (route === "/agent" && t.mode !== "live") t.setMode("live");
  }, [route, t.mode, t.setMode]);

  const onReset = () => {
    t.reset();
    setResetKey((k) => k + 1);
  };

  if (route === "/agent") {
    return (
      <div className="relative z-[1] mx-auto max-w-[1920px] px-[22px] pb-7 pt-[18px]">
        <Header label="Agent" />
        <nav className="mt-3 flex items-center gap-2">
          <NavLink href="#/" active={false} label="Race Dashboard" />
          <NavLink href="#/agent" active label="Agent Sim" />
        </nav>
        <div className="mt-4">
          <AgentSimPage
            playing={t.playing}
            setPlaying={t.setPlaying}
            speed={t.speed}
            setSpeed={t.setSpeed}
            cloud={t.cloud}
            setCloud={t.setCloud}
            liveUrl={t.liveUrl}
            setLiveUrl={t.setLiveUrl}
            latest={t.latest}
            stream={t.stream}
            step={t.step}
            hint={t.hint}
            cloudRtt={t.cloudRtt}
            aggregates={t.aggregates}
            decisions={t.diffusionRows.length}
            resetKey={resetKey}
            onReset={onReset}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="relative z-[1] mx-auto max-w-[1920px] px-[22px] pb-7 pt-[18px]">
      <Header label={labelForMode(t.mode)} />
      <nav className="mt-3 flex items-center gap-2">
        <NavLink href="#/" active label="Race Dashboard" />
        <NavLink href="#/agent" active={false} label="Agent Sim" />
      </nav>

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

      <WinnerBanner d={t.aggregates.d} a={t.aggregates.a} cloud={t.cloud} />

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1.05fr)_380px]">
        <div className="flex flex-col gap-4">
          <LatencyRace d={t.latest.d} a={t.latest.a} />
          {!numbersOnly && <ThroughputChart data={t.throughput} />}
          {!numbersOnly && <LatencyChart data={t.latency} cloud={t.cloud} />}
        </div>

        <div className="flex flex-col gap-4">
          {!numbersOnly && (
            <CellView
              latest={t.latest.d ?? t.latest.a}
              step={t.step}
              resetKey={resetKey}
              animatedFallback={t.mode === "mock"}
              preferMujocoFrame={t.mode === "replay"}
            />
          )}
          <ActionStream rows={t.stream} />
        </div>

        <StatsPanel
          d={t.aggregates.d}
          a={t.aggregates.a}
          cloud={t.cloud}
          cloudRtt={t.cloudRtt}
          step={t.step}
          decisions={t.diffusionRows.length}
        />
      </div>
    </div>
  );
}
