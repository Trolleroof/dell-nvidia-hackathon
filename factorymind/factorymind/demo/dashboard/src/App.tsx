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
    <div className="relative z-[1] max-w-[1920px] mx-auto px-[22px] pt-[18px] pb-7">
      <Header />
      <AgentSimPage
        playing={t.playing}
        setPlaying={t.setPlaying}
        speed={t.speed}
        setSpeed={t.setSpeed}
        liveUrl={t.liveUrl}
        setLiveUrl={t.setLiveUrl}
        latest={t.latest}
        step={t.step}
        resetKey={resetKey}
        onReset={onReset}
      />
    </div>
  );
}
