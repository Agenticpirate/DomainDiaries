import { Link } from "react-router-dom";
import { ArrowUpRight, Mail } from "lucide-react";
import { PROJECTS_ONLINE, WEEKLY_CLICKS } from "../../data/directory";

export function Footer() {
  return (
    <footer className="mt-16">
      <section className="mx-auto max-w-[1280px] px-4 sm:px-6">
        <div className="glass relative overflow-hidden rounded-[32px] px-6 py-10 sm:px-12">
          <div className="absolute -right-10 -top-10 size-40 rounded-full bg-[var(--gold)]/20 blur-3xl" />
          <p className="text-4xl">🏆</p>
          <h2 className="font-display mt-3 text-3xl font-bold sm:text-4xl">Ready to take the top spot?</h2>
          <p className="mt-2 max-w-xl text-[var(--mute)]">
            Paid rank, live clicks, and a desk that looks like the bid is already won.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <Stat label="Active Projects" value={`${PROJECTS_ONLINE}+`} />
            <Stat label="Weekly Clicks" value={WEEKLY_CLICKS} />
            <Stat label="Total Spent (24h)" value="$215K+" />
          </div>
        </div>
      </section>
      <div className="mx-auto mt-10 grid max-w-[1280px] gap-10 px-4 pb-10 sm:px-6 lg:grid-cols-[1.2fr_2fr_1fr]">
        <div>
          <p className="font-display text-lg font-bold">Krypto Directory</p>
          <p className="mt-2 max-w-xs text-sm text-[var(--mute)]">
            The premium leaderboard for crypto products. Visibility is an auction.
          </p>
          <div className="mt-4 flex gap-3 text-sm text-[var(--mute)]">
            <a href="https://x.com" target="_blank" rel="noreferrer">X</a>
            <a href="https://t.me" target="_blank" rel="noreferrer">Telegram</a>
            <a href="https://discord.com" target="_blank" rel="noreferrer">Discord</a>
            <a href="https://youtube.com" target="_blank" rel="noreferrer">YouTube</a>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4 text-sm">
          <Col title="Company" links={[{ to: "/about", label: "About" }, { to: "/promote", label: "Careers" }]} />
          <Col title="Product" links={[{ to: "/", label: "Leaderboard" }, { to: "/promote", label: "Promote" }]} />
          <Col title="Resources" links={[{ to: "/resources", label: "Guides" }, { to: "/networks", label: "Networks" }]} />
          <Col title="Legal" links={[{ to: "/about", label: "Privacy" }, { to: "/about", label: "Terms" }]} />
        </div>
        <form
          className="glass rounded-3xl p-4"
          onSubmit={(event) => event.preventDefault()}
        >
          <p className="text-sm font-semibold">Stay Updated</p>
          <div className="mt-3 flex gap-2">
            <label className="sr-only" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@project.xyz"
              className="min-w-0 flex-1 rounded-full border border-[var(--line)] bg-transparent px-4 py-2 text-sm outline-none"
            />
            <button type="submit" className="grid size-10 place-items-center rounded-full bg-[var(--violet)] text-white" aria-label="Subscribe">
              <Mail className="size-4" />
            </button>
          </div>
        </form>
      </div>
      <p className="border-t border-[var(--line)] py-6 text-center text-xs text-[var(--mute)]">
        © 2026 Krypto Directory. Sample catalog — bids on this device only.
      </p>
    </footer>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-black/10 px-4 py-4">
      <p className="font-display text-2xl font-bold">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-[0.16em] text-[var(--mute)]">{label}</p>
    </div>
  );
}

function Col({ title, links }: { title: string; links: Array<{ to: string; label: string }> }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--mute)]">{title}</p>
      <div className="flex flex-col gap-2">
        {links.map((link) => (
          <Link key={link.label} to={link.to} className="inline-flex items-center gap-1 hover:text-[var(--violet)]">
            {link.label} <ArrowUpRight className="size-3 opacity-0" />
          </Link>
        ))}
      </div>
    </div>
  );
}
