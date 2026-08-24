import { CATEGORIES } from "../data/directory";
import { useDirectory } from "../context/DirectoryContext";
import { formatUsd } from "../lib/format";
import { Link } from "react-router-dom";

export function CategoriesPage() {
  const { projects } = useDirectory();
  return (
    <div className="mx-auto max-w-[1280px] px-4 py-10 sm:px-6">
      <h1 className="font-display text-4xl font-bold">Categories</h1>
      <p className="mt-2 max-w-2xl text-[var(--mute)]">Filter the leaderboard by product type.</p>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {CATEGORIES.map((category) => {
          const listed = projects.filter((project) => project.category === category.id);
          return (
            <section id={category.id} key={category.id} className="glass scroll-mt-24 rounded-[28px] p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-2xl font-bold">{category.label}</h2>
                <span className="font-mono text-sm text-[var(--mute)]">{category.projects}</span>
              </div>
              <div className="mt-4 flex flex-col gap-2">
                {listed.slice(0, 5).map((project, index) => (
                  <Link key={project.id} to={`/project/${project.id}`} className="flex items-center justify-between rounded-2xl px-2 py-2 hover:bg-white/4">
                    <span>
                      <span className="mr-2 font-mono text-xs text-[var(--mute)]">#{index + 1}</span>
                      {project.name}
                    </span>
                    <span className="font-mono text-sm text-[var(--orange)]">{formatUsd(project.bidUsd)}</span>
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
