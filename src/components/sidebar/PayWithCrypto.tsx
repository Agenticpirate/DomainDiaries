const COINS = ["USDC", "USDT", "ETH", "SOL", "BTC"];

export function PayWithCrypto() {
  return (
    <section className="glass rounded-[28px] p-5">
      <h2 className="text-sm font-semibold">Pay With Crypto</h2>
      <p className="mt-2 text-sm text-[var(--mute)]">Stablecoins and majors. No card desk required.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {COINS.map((coin) => (
          <span key={coin} className="rounded-full border border-[var(--line)] px-3 py-1 font-mono text-xs">
            {coin}
          </span>
        ))}
      </div>
      <p className="mt-4 text-[11px] uppercase tracking-[0.16em] text-[var(--green)]">Escrow · Proof of bid · Live rank</p>
    </section>
  );
}
