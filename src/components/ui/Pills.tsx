import { categoryOf, networkOf } from "../../data/directory";
import type { CategoryId, NetworkId } from "../../types";

export function ProjectMark({ name, hue }: { name: string; hue: string }) {
  const letter = name.slice(0, 1).toUpperCase();
  return (
    <span
      className="grid size-10 shrink-0 place-items-center rounded-xl text-sm font-bold text-white"
      style={{
        background: `linear-gradient(145deg, ${hue}, color-mix(in srgb, ${hue} 40%, #111))`,
        boxShadow: `0 8px 18px color-mix(in srgb, ${hue} 35%, transparent)`,
      }}
    >
      {letter}
    </span>
  );
}

export function NetworkPill({ id }: { id: NetworkId }) {
  const network = networkOf(id);
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold"
      style={{
        color: network.hue,
        background: `color-mix(in srgb, ${network.hue} 16%, transparent)`,
      }}
    >
      {network.label}
    </span>
  );
}

export function CategoryPill({ id }: { id: CategoryId }) {
  const category = categoryOf(id);
  return (
    <span className="inline-flex items-center rounded-full bg-[color-mix(in_srgb,var(--cyan)_14%,transparent)] px-2.5 py-1 text-[11px] font-semibold text-[var(--cyan)]">
      {category.label}
    </span>
  );
}
