export function ResourcesPage() {
  const guides = [
    { title: "How bidding works", body: "Highest bid sits on top. Outbids are public. Rank is rented, not owned." },
    { title: "What the podium is worth", body: "Gold, silver, and bronze are the only three cards above the fold." },
    { title: "Networks vs categories", body: "A listing belongs to one chain and one product type. Both have their own boards." },
  ];
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="font-display text-5xl font-bold">Resources</h1>
      <div className="mt-8 flex flex-col gap-4">
        {guides.map((guide) => (
          <article key={guide.title} className="glass rounded-[28px] p-6">
            <h2 className="font-display text-2xl font-bold">{guide.title}</h2>
            <p className="mt-2 text-[var(--mute)]">{guide.body}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
