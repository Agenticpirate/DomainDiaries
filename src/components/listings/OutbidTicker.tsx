import { minutesLabel, formatUsd } from "../../lib/format";
import type { OutbidEvent } from "../../types";

export function OutbidTicker({ events }: { events: OutbidEvent[] }) {
  const loop = [...events, ...events];
  return (
    <div className="glass overflow-hidden rounded-2xl">
      <div className="flex items-center gap-3 border-b border-[var(--line)] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--mute)]">
        Latest outbids
      </div>
      <div className="overflow-hidden py-3">
        <div className="marquee gap-6 px-4">
          {loop.map((event, index) => (
            <span key={`${event.id}-${index}`} className="inline-flex items-center gap-2 text-sm">
              <span className="grid size-6 place-items-center rounded-full bg-[var(--violet)] text-[10px] font-bold">
                {event.projectName.slice(0, 1)}
              </span>
              <strong>{event.projectName}</strong>
              <span className="text-[var(--orange)]">{formatUsd(event.amount)}</span>
              <span className="text-[var(--mute)]">{minutesLabel(event.minutesAgo)}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
