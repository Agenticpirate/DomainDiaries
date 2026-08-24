type Props = {
  prices?: number[];
  up: boolean;
  width?: number;
  height?: number;
};

export function Sparkline({ prices, up, width = 112, height = 36 }: Props) {
  if (!prices || prices.length < 2) {
    return <div className="h-9 w-28" />;
  }
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const span = max - min || 1;
  const d = prices
    .map((price, index) => {
      const x = (index / (prices.length - 1)) * width;
      const y = height - ((price - min) / span) * (height - 4) - 2;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  const color = up ? "#3EE6A0" : "#FF5D73";
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}
