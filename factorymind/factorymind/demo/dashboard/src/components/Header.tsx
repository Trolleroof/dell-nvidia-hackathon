export function Header() {
  return (
    <header className="flex items-center gap-5 flex-wrap pb-3.5 border-b border-line">
      <div className="flex items-center gap-3.5">
        <span className="font-extrabold text-xl tracking-[1.5px] whitespace-nowrap">
          <span className="text-dell-bright">DELL</span>
          <span className="text-faint mx-1.5 font-semibold">&times;</span>
          <span className="text-nvidia-bright">NVIDIA</span>
        </span>
        <span
          className="border-2 border-line rounded-[10px] px-3.5 py-2"
          style={{ background: "linear-gradient(180deg, rgba(255,255,255,.03), transparent)" }}
        >
          <span className="text-[26px] font-extrabold tracking-[2px]">
            <span
              style={{
                background: "linear-gradient(90deg, #38b6ff, #95e600)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              AI
            </span>{" "}
            FACTORYMIND
          </span>
        </span>
      </div>
    </header>
  );
}
