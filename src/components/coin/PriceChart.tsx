type Props = {
  points: [number, number][];
  up: boolean;
};

export function PriceChart({ points, up }: Props) {
  if (points.length < 2) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-mute">
        Chart data is not available yet.
      </div>
    );
  }
  const width = 920;
  const height = 280;
  const pad = 12;
  const values = points.map(([, price]) => price);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const coords = points.map(([time, price], index) => {
    const x = pad + (index / (points.length - 1)) * (width - pad * 2);
    const y = pad + (1 - (price - min) / span) * (height - pad * 2);
    return { x, y, time, price };
  });
  const line = coords.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const area = `${line} L${coords[coords.length - 1].x.toFixed(1)} ${height - pad} L${coords[0].x.toFixed(1)} ${height - pad} Z`;
  const stroke = up ? "#3EE6A0" : "#FF5D73";
  const fill = up ? "rgba(62,230,160,0.12)" : "rgba(255,93,115,0.12)";
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full" role="img" aria-label="Price chart">
      <path d={area} fill={fill} />
      <path d={line} fill="none" stroke={stroke} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}
