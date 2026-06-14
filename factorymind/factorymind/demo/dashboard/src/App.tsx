import { useState } from "react";
import { useTelemetry } from "./hooks/useTelemetry";
import { Header } from "./components/Header";
import { AgentSimPage } from "./components/AgentSimPage";

export default function App() {
  const t = useTelemetry();
  const [resetKey, setResetKey] = useState(0);

  const onReset = () => {
    t.reset();
    setResetKey((k) => k + 1);
  };

  return (
    <>
      <div className="ambient-blob one" />
      <div className="ambient-blob two" />
      <div className="relative z-[1] mx-auto max-w-[1920px] px-4 pb-8 pt-5 sm:px-6 lg:px-8">
        <Header />
        <AgentSimPage
          playing={t.playing}
          setPlaying={t.setPlaying}
          speed={t.speed}
          setSpeed={t.setSpeed}
          liveUrl={t.liveUrl}
          setLiveUrl={t.setLiveUrl}
          latest={t.latest}
          stream={t.stream}
          step={t.step}
          resetKey={resetKey}
          onReset={onReset}
        />
      </div>
    </>
  );
}
