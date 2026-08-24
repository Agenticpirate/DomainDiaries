export function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--cyan)]">About</p>
      <h1 className="font-display mt-3 text-5xl font-bold">A directory that charges for the spotlight.</h1>
      <p className="mt-5 text-lg leading-relaxed text-[var(--mute)]">
        Krypto Directory is a premium listing desk for crypto products. Rank is public, bids are visible, and the
        top three get a podium that looks like it costs what it costs.
      </p>
      <p className="mt-4 text-lg leading-relaxed text-[var(--mute)]">
        This build is the sample catalog: live UI, local bids, no custody. Payments, escrow, and verified projects
        come next.
      </p>
    </div>
  );
}
