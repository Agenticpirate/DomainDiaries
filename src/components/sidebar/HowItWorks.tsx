type Props = { onList: () => void };

export function HowItWorks({ onList }: Props) {
  const steps = [
    { n: "01", title: "Choose your spot", copy: "Pick the rank you want to own on the public tape." },
    { n: "02", title: "Place your bid", copy: "Outbid the current holder. Highest bid sits on top." },
    { n: "03", title: "Get more visibility", copy: "Clicks, podium glow, and a listing that looks expensive." },
  ];
  return (
    <section className="glass rounded-[28px] p-5">
      <h2 className="text-sm font-semibold">How It Works</h2>
      <ol className="mt-4 flex flex-col gap-4">
        {steps.map((step) => (
          <li key={step.n} className="flex gap-3">
            <span className="font-mono text-xs text-[var(--violet)]">{step.n}</span>
            <span>
              <span className="block text-sm font-semibold">{step.title}</span>
              <span className="mt-1 block text-sm text-[var(--mute)]">{step.copy}</span>
            </span>
          </li>
        ))}
      </ol>
      <button
        type="button"
        onClick={onList}
        className="mt-5 w-full rounded-full bg-gradient-to-r from-[#9b7dff] to-[#6d5cff] px-4 py-2.5 text-sm font-bold text-white"
      >
        List Your Project
      </button>
    </section>
  );
}
