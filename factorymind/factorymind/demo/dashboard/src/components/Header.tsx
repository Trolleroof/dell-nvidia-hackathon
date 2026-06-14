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
        fontFamily="'JetBrains Mono', ui-monospace, monospace"
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
    <header className="border-b-4 border-foreground pb-8">
      {/* Eyebrow — SVG wordmarks, a rule, and the edition slug on the right */}
      <div className="flex items-center gap-3 font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
        <Wordmark text="DELL" color="#007db8" width={42} label="Dell" />
        <span className="text-faint">&times;</span>
        <Wordmark text="NVIDIA" color="#76b900" width={64} label="NVIDIA" />
        <span className="h-px flex-1 bg-border-light" />
        <span className="hidden sm:inline">GB10 · Local Inference</span>
      </div>

      {/* Masthead — boxed "AI" mark (NVIDIA green) + oversized mono wordmark */}
      <div className="mt-6 flex flex-wrap items-stretch gap-x-5 gap-y-4">
        <span
          aria-hidden
          className="flex items-center justify-center bg-nvidia px-3.5 font-mono text-3xl font-extrabold leading-none text-background md:text-5xl"
        >
          AI
        </span>
        <h1 className="self-center font-mono text-4xl font-extrabold leading-[0.95] tracking-tight text-foreground sm:text-5xl md:text-6xl lg:text-7xl">
          FACTORYMIND
        </h1>
        <span className="ml-auto hidden shrink-0 flex-col items-end justify-center border-l border-border-light pl-5 font-mono text-[10px] font-semibold uppercase leading-relaxed tracking-[0.18em] text-muted-foreground lg:flex">
          <span>Fig. 01</span>
          <span>Assembly Cell</span>
          <span className="text-foreground">2 Arms · 3 Parts</span>
        </span>
      </div>

      {/* Standfirst — mono lede */}
      <p className="mt-6 max-w-3xl font-mono text-sm leading-relaxed text-muted-foreground md:text-base">
        Diffusion versus autoregressive control — planned in parallel, executed
        locally on the box. No cloud, no waiting on the network.
      </p>
    </header>
  );
}
