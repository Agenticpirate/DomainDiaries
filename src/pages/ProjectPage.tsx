import { Link, useParams } from "react-router-dom";
import { useDirectory } from "../context/DirectoryContext";
import { formatCompact, formatUsd } from "../lib/format";
import { CategoryPill, NetworkPill, ProjectMark } from "../components/ui/Pills";
import { networkOf } from "../data/directory";

export function ProjectPage() {
  const { id = "" } = useParams();
  const { projects } = useDirectory();
  const project = projects.find((item) => item.id === id);
  const rank = project ? projects.findIndex((item) => item.id === project.id) + 1 : 0;

  if (!project) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <p>Project not found.</p>
        <Link to="/" className="mt-4 inline-block text-[var(--violet)]">
          Back to leaderboard
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <Link to="/" className="text-sm text-[var(--mute)]">
        ← Leaderboard
      </Link>
      <div className="mt-6 flex items-center gap-4">
        <ProjectMark name={project.name} hue={networkOf(project.network).hue} />
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--gold)]">Rank #{rank}</p>
          <h1 className="font-display text-4xl font-bold">{project.name}</h1>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <NetworkPill id={project.network} />
        <CategoryPill id={project.category} />
      </div>
      <p className="mt-6 text-lg text-[var(--mute)]">{project.description}</p>
      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        <Stat label="Current bid" value={formatUsd(project.bidUsd)} />
        <Stat label="7D clicks" value={formatCompact(project.clicks7d)} />
        <Stat label="Listed" value={project.listedAt} />
      </div>
      <a
        href={project.url}
        target="_blank"
        rel="noreferrer"
        className="mt-8 inline-flex rounded-full bg-[var(--green)] px-5 py-2.5 text-sm font-bold text-[#052016]"
      >
        Visit project
      </a>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <article className="glass rounded-2xl p-4">
      <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--mute)]">{label}</p>
      <p className="mt-2 font-mono text-xl">{value}</p>
    </article>
  );
}
