// Brand names rendered as styled SVG wordmarks (type only — no logo artwork),
// per the official Dell × NVIDIA hackathon guidance.
function Wordmark({
  text,
  color,
  width,
  label,
}: {
  text: string;
  color: string;
  width: number;
  label: string;
}) {
  return (
    <svg
      width={width}
      height={15}
      viewBox={`0 0 ${width} 15`}
      role="img"
      aria-label={label}
      className="block shrink-0"
    >
      <text
        x="0"
        y="12"
        fill={color}
        fontFamily="'Nunito', ui-sans-serif, system-ui"
        fontSize="14"
        fontWeight="800"
        letterSpacing="1.5"
      >
        {text}
      </text>
    </svg>
  );
}

export function Header() {
  return (
    <header className="relative overflow-hidden rounded-[2.7rem_1.7rem_2.35rem_1.9rem] border border-border-light bg-card px-5 py-6 shadow-[var(--shadow-soft)] backdrop-blur-xl sm:px-7">
      <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-[62%_38%_48%_52%_/_44%_60%_40%_56%] bg-sun/25 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 left-1/3 h-56 w-72 rounded-[38%_62%_70%_30%_/_58%_34%_66%_42%] bg-dell-bright/15 blur-3xl" />

      <div className="relative flex items-center gap-3 text-[11px] font-extrabold uppercase tracking-[0.18em] text-muted-foreground">
        <Wordmark text="DELL" color="#007db8" width={42} label="Dell" />
        <span className="text-faint">&times;</span>
        <Wordmark text="NVIDIA" color="#5d7052" width={64} label="NVIDIA" />
        <span className="h-px flex-1 bg-border-light" />
        <span className="hidden rounded-full border border-border-light bg-white/45 px-3 py-1 sm:inline">GB10 · Local Inference</span>
      </div>

      <div className="relative mt-6 flex flex-wrap items-stretch gap-x-5 gap-y-4">
        <span
          aria-hidden
          className="flex items-center justify-center rounded-[55%_45%_42%_58%_/_48%_58%_42%_52%] bg-nvidia px-4 font-display text-3xl font-extrabold leading-none text-white shadow-[0_20px_36px_-24px_rgba(93,112,82,.8)] md:text-5xl"
        >
          AI
        </span>
        <h1 className="self-center font-display text-4xl font-extrabold leading-[0.95] tracking-normal text-foreground sm:text-5xl md:text-6xl lg:text-7xl">
          FACTORYMIND
        </h1>
        <span className="ml-auto hidden shrink-0 flex-col items-end justify-center rounded-[1.7rem_1.1rem_1.6rem_1.25rem] border border-border-light bg-white/45 px-5 py-3 text-[10px] font-extrabold uppercase leading-relaxed tracking-[0.16em] text-muted-foreground lg:flex">
          <span>Fig. 01</span>
          <span>Assembly Cell</span>
          <span className="text-foreground">2 Arms · 3 Parts</span>
        </span>
      </div>

      <p className="relative mt-6 max-w-3xl text-base font-semibold leading-relaxed text-muted-foreground md:text-lg">
        Diffusion versus autoregressive control — planned in parallel, executed
        locally on the box. No cloud, no waiting on the network.
      </p>
    </header>
  );
}
