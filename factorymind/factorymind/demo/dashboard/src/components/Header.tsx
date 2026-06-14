export function Header() {
  return (
    <header className="border-b-4 border-foreground pb-8">
      {/* Eyebrow — mono caps, a rule, and the edition slug on the right */}
      <div className="flex items-center gap-4 font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
        <span className="text-foreground">Dell</span>
        <span className="text-faint">&times;</span>
        <span className="text-foreground">NVIDIA</span>
        <span className="h-px flex-1 bg-border-light" />
        <span className="hidden sm:inline">GB10 · Local Inference</span>
      </div>

      {/* Masthead — boxed "AI" mark (inversion) + oversized serif wordmark */}
      <div className="mt-6 flex flex-wrap items-stretch gap-x-6 gap-y-4">
        <span
          aria-hidden
          className="flex items-center justify-center bg-foreground px-4 font-display text-3xl font-black leading-none text-background md:text-5xl"
        >
          AI
        </span>
        <h1 className="self-center font-display text-5xl font-black leading-[0.9] tracking-tight text-foreground sm:text-6xl md:text-7xl lg:text-8xl">
          FACTORYMIND
        </h1>
        <span className="ml-auto hidden shrink-0 flex-col items-end justify-center border-l border-border-light pl-5 font-mono text-[10px] font-semibold uppercase leading-relaxed tracking-[0.18em] text-muted-foreground lg:flex">
          <span>Fig. 01</span>
          <span>Assembly Cell</span>
          <span className="text-foreground">2 Arms · 3 Parts</span>
        </span>
      </div>

      {/* Standfirst — italic serif lede */}
      <p className="mt-6 max-w-3xl font-serif text-lg italic leading-relaxed text-muted-foreground md:text-xl">
        Diffusion versus autoregressive control — planned in parallel, executed
        locally on the box. No color, no cloud, no waiting on the network.
      </p>
    </header>
  );
}
