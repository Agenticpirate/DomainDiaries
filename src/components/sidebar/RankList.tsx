import { Link } from "react-router-dom";
import { CATEGORIES, NETWORKS } from "../../data/directory";

export function RankList({
  title,
  kind,
}: {
  title: string;
  kind: "networks" | "categories";
}) {
  const rows =
    kind === "networks"
      ? NETWORKS.map((item) => ({ id: item.id, label: item.label, count: item.projects, hue: item.hue, to: `/networks#${item.id}` }))
      : CATEGORIES.map((item) => ({
          id: item.id,
          label: item.label,
          count: item.projects,
          hue: "#3ee7ff",
          to: `/categories#${item.id}`,
        }));

  return (
    <section className="glass rounded-[28px] p-5">
      <h2 className="text-sm font-semibold">{title}</h2>
      <ol className="mt-4 flex flex-col gap-2">
        {rows.slice(0, 6).map((row, index) => (
          <li key={row.id}>
            <Link
              to={row.to}
              className="flex items-center gap-3 rounded-2xl px-2 py-2 hover:bg-white/4"
            >
              <span className="w-5 font-mono text-xs text-[var(--mute)]">{index + 1}</span>
              <span className="size-2.5 rounded-full" style={{ background: row.hue }} />
              <span className="flex-1 text-sm">{row.label}</span>
              <span className="font-mono text-xs text-[var(--mute)]">{row.count}</span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
