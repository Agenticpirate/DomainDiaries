import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import type { CategoryId, Project } from "../../types";
import { CATEGORIES } from "../../data/directory";
import { formatCompact, formatUsd } from "../../lib/format";
import { CategoryPill, NetworkPill, ProjectMark } from "../ui/Pills";
import { networkOf } from "../../data/directory";
import { cn } from "../../lib/cn";

type Props = {
  projects: Project[];
  category: "all" | CategoryId;
  onCategory: (value: "all" | CategoryId) => void;
};

export function ProjectTable({ projects, category, onCategory }: Props) {
  const rows = category === "all" ? projects : projects.filter((project) => project.category === category);
  const ranked = rows.map((project) => ({ project, rank: projects.indexOf(project) + 1 }));
  const visible = category === "all" ? ranked.filter((row) => row.rank > 3) : ranked;

  return (
    <section className="glass overflow-hidden rounded-[28px]">
      <div className="tabs-row flex gap-2 px-4 py-4">
        <Tab active={category === "all"} onClick={() => onCategory("all")}>
          All
        </Tab>
        {CATEGORIES.map((item) => (
          <Tab key={item.id} active={category === item.id} onClick={() => onCategory(item.id)}>
            {item.label}
          </Tab>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[820px] w-full text-left">
          <thead className="text-[11px] uppercase tracking-[0.16em] text-[var(--mute)]">
            <tr className="border-y border-[var(--line)]">
              <th className="px-4 py-3 font-medium">#</th>
              <th className="px-4 py-3 font-medium">Project</th>
              <th className="px-4 py-3 font-medium">Network</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 text-right font-medium">7D Clicks</th>
              <th className="px-4 py-3 text-right font-medium">Current Bid</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {visible.map(({ project, rank }) => (
              <tr key={project.id} className="border-b border-[var(--line)]/60 hover:bg-white/3">
                <td className="px-4 py-4 font-mono text-sm text-[var(--mute)]">{rank}</td>
                <td className="px-4 py-4">
                  <Link to={`/project/${project.id}`} className="flex items-center gap-3">
                    <ProjectMark name={project.name} hue={networkOf(project.network).hue} />
                    <span>
                      <span className="block font-semibold">{project.name}</span>
                      <span className="block max-w-xs text-sm text-[var(--mute)]">{project.tagline}</span>
                    </span>
                  </Link>
                </td>
                <td className="px-4 py-4">
                  <NetworkPill id={project.network} />
                </td>
                <td className="px-4 py-4">
                  <CategoryPill id={project.category} />
                </td>
                <td className="px-4 py-4 text-right font-mono text-sm">{formatCompact(project.clicks7d)}</td>
                <td className="px-4 py-4 text-right font-mono text-sm font-semibold text-[var(--orange)]">
                  {formatUsd(project.bidUsd)}
                </td>
                <td className="px-4 py-4">
                  <Link to={`/project/${project.id}`} aria-label={`Open ${project.name}`} className="grid size-8 place-items-center rounded-full border border-[var(--line)]">
                    <ChevronRight className="size-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Tab({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "shrink-0 rounded-full px-3.5 py-1.5 text-sm text-[var(--mute)]",
        active && "bg-white/10 text-[var(--ink)]",
      )}
    >
      {children}
    </button>
  );
}
