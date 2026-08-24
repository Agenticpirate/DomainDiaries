import { NETWORKS } from "../data/directory";
import { useDirectory } from "../context/DirectoryContext";
import { formatCompact } from "../lib/format";
import { ProjectMark } from "../components/ui/Pills";
import { Link } from "react-router-dom";
import { networkOf } from "../data/directory";

export function NetworksPage() {
  const { projects } = useDirectory();
  return (
    <div className="mx-auto max-w-[1280px] px-4 py-10 sm:px-6">
      <h1 className="font-display text-4xl font-bold">Networks</h1>
      <p className="mt-2 max-w-2xl text-[var(--mute)]">Every chain on the tape, ranked by listed projects.</p>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {NETWORKS.map((network) => {
          const listed = projects.filter((project) => project.network === network.id);
          return (
            <section id={network.id} key={network.id} className="glass scroll-mt-24 rounded-[28px] p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-2xl font-bold" style={{ color: network.hue }}>
                  {network.label}
                </h2>
                <span className="font-mono text-sm text-[var(--mute)]">{network.projects} listed</span>
              </div>
              <div className="mt-4 flex flex-col gap-2">
                {listed.slice(0, 4).map((project) => (
                  <Link key={project.id} to={`/project/${project.id}`} className="flex items-center gap-3 rounded-2xl px-2 py-2 hover:bg-white/4">
                    <ProjectMark name={project.name} hue={networkOf(project.network).hue} />
                    <span className="flex-1">{project.name}</span>
                    <span className="font-mono text-xs text-[var(--mute)]">{formatCompact(project.clicks7d)}</span>
                  </Link>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
