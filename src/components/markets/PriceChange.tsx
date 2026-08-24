import { changeTone, formatPct } from "../../lib/format";
import { cn } from "../../lib/cn";

export function PriceChange({ value }: { value: number | null | undefined }) {
  const tone = changeTone(value);
  return (
    <span
      className={cn(
        "font-mono text-sm tabular-nums",
        tone === "up" && "text-up",
        tone === "down" && "text-down",
        tone === "flat" && "text-mute",
      )}
    >
      {formatPct(value)}
    </span>
  );
}
