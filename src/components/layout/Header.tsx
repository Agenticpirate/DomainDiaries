import { Link, NavLink } from "react-router-dom";
import { Search } from "lucide-react";
import { cn } from "../../lib/cn";

const links = [
  { to: "/", label: "Markets" },
  { to: "/watchlist", label: "Watchlist" },
  { to: "/portfolio", label: "Portfolio" },
];

type Props = {
  onSearch: () => void;
};

export function Header({ onSearch }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/8 bg-[#050506]/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-lg border border-brand/60 bg-black font-mono text-sm font-semibold text-brand">
            K
          </span>
          <span className="text-lg font-bold tracking-tight">Krypto</span>
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-3.5 py-1.5 text-sm text-mute transition-colors hover:text-ink",
                  isActive && "bg-white/6 text-ink",
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <button
          type="button"
          onClick={onSearch}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/4 px-3 py-1.5 text-sm text-mute hover:border-white/20 hover:text-ink"
        >
          <Search className="size-4" />
          <span className="hidden sm:inline">Search</span>
          <kbd className="hidden rounded border border-white/10 px-1.5 font-mono text-[10px] md:inline">/</kbd>
        </button>
      </div>
      <nav className="flex gap-1 overflow-x-auto border-t border-white/6 px-4 py-2 md:hidden">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              cn(
                "rounded-full px-3 py-1 text-sm text-mute",
                isActive && "bg-white/6 text-ink",
              )
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
