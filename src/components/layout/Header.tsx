import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { ChevronDown, Menu, Moon, Sun, X } from "lucide-react";
import { cn } from "../../lib/cn";
import { initTheme, writeTheme, type Theme } from "../../lib/theme";

const NAV = [
  { to: "/", label: "Leaderboard" },
  { to: "/networks", label: "Networks" },
  { to: "/categories", label: "Categories" },
  { to: "/promote", label: "Promote" },
];

type Props = {
  onList: () => void;
};

export function Header({ onList }: Props) {
  const [theme, setTheme] = useState<Theme>("dark");
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const [resourcesOpen, setResourcesOpen] = useState(false);

  useEffect(() => {
    setTheme(initTheme());
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    writeTheme(next);
    setTheme(next);
  }

  return (
    <header
      className={cn(
        "sticky top-0 z-40 border-b border-transparent",
        scrolled && "border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_78%,transparent)] backdrop-blur-xl",
      )}
    >
      <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-lg bg-gradient-to-br from-[#9b7dff] to-[#5b4dff] font-display text-sm font-bold text-white shadow-[0_8px_20px_rgba(120,80,255,0.45)]">
            <svg viewBox="0 0 24 24" className="size-5" fill="none">
              <path
                d="M12 2 20 7v10l-8 5-8-5V7l8-5Z"
                stroke="currentColor"
                strokeWidth="1.6"
              />
              <path d="M12 8v8M9 12h6" stroke="currentColor" strokeWidth="1.6" />
            </svg>
          </span>
          <span className="font-display text-[15px] font-bold tracking-tight">
            Krypto <span className="text-[var(--mute)]">Directory</span>
          </span>
        </Link>
        <div className="hidden items-center gap-2 rounded-full border border-[var(--line)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--mute)] lg:flex">
          <span className="live-dot size-1.5 rounded-full bg-[var(--green)]" />
          24H Live
        </div>
        <nav className="hidden items-center gap-1 lg:flex">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-3 py-1.5 text-sm text-[var(--mute)] hover:text-[var(--ink)]",
                  isActive && "bg-white/6 text-[var(--ink)]",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
          <div className="relative">
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm text-[var(--mute)] hover:text-[var(--ink)]"
              aria-expanded={resourcesOpen}
              onClick={() => setResourcesOpen((value) => !value)}
            >
              Resources <ChevronDown className="size-3.5" />
            </button>
            {resourcesOpen && (
              <div className="glass absolute right-0 mt-2 w-48 rounded-2xl p-2">
                <Link to="/resources" className="block rounded-xl px-3 py-2 text-sm hover:bg-white/5" onClick={() => setResourcesOpen(false)}>
                  Guides
                </Link>
                <Link to="/about" className="block rounded-xl px-3 py-2 text-sm hover:bg-white/5" onClick={() => setResourcesOpen(false)}>
                  About
                </Link>
              </div>
            )}
          </div>
          <NavLink to="/about" className="rounded-full px-3 py-1.5 text-sm text-[var(--mute)] hover:text-[var(--ink)]">
            About
          </NavLink>
        </nav>
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            onClick={toggleTheme}
            className="grid size-10 place-items-center rounded-full border border-[var(--line)] text-[var(--mute)] hover:text-[var(--ink)]"
          >
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <button
            type="button"
            onClick={onList}
            className="hidden rounded-full bg-gradient-to-r from-[#9b7dff] to-[#6d5cff] px-4 py-2 text-sm font-bold text-white shadow-[0_10px_24px_rgba(120,80,255,0.35)] sm:inline-flex"
          >
            List Your Project
          </button>
          <button
            type="button"
            className="grid size-10 place-items-center rounded-full border border-[var(--line)] lg:hidden"
            aria-label="Open menu"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>
      {open && (
        <div className="glass mx-4 mb-4 rounded-2xl p-3 lg:hidden">
          {[...NAV, { to: "/resources", label: "Resources" }, { to: "/about", label: "About" }].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setOpen(false)}
              className="block rounded-xl px-3 py-2 text-sm"
            >
              {item.label}
            </NavLink>
          ))}
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onList();
            }}
            className="mt-2 w-full rounded-full bg-gradient-to-r from-[#9b7dff] to-[#6d5cff] px-4 py-2 text-sm font-bold text-white"
          >
            List Your Project
          </button>
        </div>
      )}
    </header>
  );
}
