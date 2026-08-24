const ICONS = [
  { label: "ETH", color: "#8B9CFF", r: 118 },
  { label: "SOL", color: "#14F195", r: 118 },
  { label: "BNB", color: "#F3BA2F", r: 118 },
  { label: "BASE", color: "#4C8DFF", r: 118 },
  { label: "AVAX", color: "#E84142", r: 118 },
  { label: "TON", color: "#0098EA", r: 118 },
];

export function CoinOrbit() {
  return (
    <div className="relative mx-auto size-[340px] sm:size-[400px]">
      <div className="absolute inset-10 rounded-full bg-[radial-gradient(circle,rgba(155,125,255,0.35),transparent_68%)] blur-2xl" />
      <div className="absolute inset-[72px] rounded-full bg-[radial-gradient(circle_at_30%_20%,#ffe9a8,#f5c542_42%,#b8860b)] shadow-[0_30px_80px_rgba(245,197,66,0.35)]" />
      <div className="absolute inset-[92px] rounded-full bg-[radial-gradient(circle_at_35%_28%,#fff6d2,#f0b429_55%,#8a5a00)] grid place-items-center">
        <span className="font-display text-5xl font-bold text-[#6a4200]">₿</span>
      </div>
      <div className="absolute inset-x-24 bottom-8 h-10 rounded-full bg-[radial-gradient(ellipse,rgba(155,125,255,0.7),transparent_70%)] blur-md" />
      <div className="orbit absolute inset-6">
        {ICONS.map((icon, index) => {
          const angle = (index / ICONS.length) * Math.PI * 2 - Math.PI / 2;
          const x = 50 + Math.cos(angle) * 46;
          const y = 50 + Math.sin(angle) * 46;
          return (
            <span
              key={icon.label}
              className="absolute grid size-12 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-2xl text-[10px] font-bold text-white shadow-lg"
              style={{
                left: `${x}%`,
                top: `${y}%`,
                background: icon.color,
              }}
            >
              {icon.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
