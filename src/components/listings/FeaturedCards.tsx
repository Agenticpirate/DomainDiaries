import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import type { Project } from "../../types";
import { formatCompact, formatUsd } from "../../lib/format";
import { networkOf } from "../../data/directory";
import { CategoryPill, NetworkPill, ProjectMark } from "../ui/Pills";
import { cn } from "../../lib/cn";

const PODIUM = [
  { rank: 1, glow: "glow-gold", badge: "from-[#f5c542] to-[#d4a017]", label: "Gold" },
  { rank: 2, glow: "glow-silver", badge: "from-[#d7e3ff] to-[#8ea2c9]", label: "Silver" },
  { rank: 3, glow: "glow-bronze", badge: "from-[#ff8a4c] to-[#c45c20]", label: "Bronze" },
] as const;

export function FeaturedCards({ projects }: { projects: Project[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {projects.slice(0, 3).map((project, index) => {
        const podium = PODIUM[index];
        const network = networkOf(project.network);
        return (
          <article key={project.id} className={cn("glass relative overflow-hidden rounded-[28px] p-5", podium.glow)}>
            <div
              className={cn(
                "absolute right-4 top-4 grid size-10 place-items-center rounded-2xl bg-gradient-to-br text-sm font-black text-black",
                podium.badge,
              )}
            >
              #{podium.rank}
            </div>
            <div className="flex items-center gap-3 pr-12">
              <ProjectMark name={project.name} hue={network.hue} />
              <div>
                <h3 className="font-display text-xl font-bold">{project.name}</h3>
                <p className="text-xs uppercase tracking-[0.14em] text-[var(--mute)]">{podium.label} podium</p>
              </div>
            </div>
            <p className="mt-4 text-sm text-[var(--mute)]">{project.tagline}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <NetworkPill id={project.network} />
              <CategoryPill id={project.category} />
            </div>
            <div className="mt-5 flex items-end justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--mute)]">7D clicks</p>
                <p className="font-mono text-sm">{formatCompact(project.clicks7d)}</p>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--mute)]">Current bid</p>
                <p className="font-mono text-lg font-semibold text-[var(--orange)]">{formatUsd(project.bidUsd)}</p>
              </div>
            </div>
            <Link
              to={`/project/${project.id}`}
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[var(--green)] px-4 py-2.5 text-sm font-bold text-[#052016]"
            >
              View <ArrowUpRight className="size-4" />
            </Link>
          </article>
        );
      })}
    </div>
  );
}
