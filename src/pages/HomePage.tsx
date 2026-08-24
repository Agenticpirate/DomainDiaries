import { useState } from "react";
import { useDirectory } from "../context/DirectoryContext";
import type { CategoryId } from "../types";
import { Hero } from "../components/hero/Hero";
import { FeaturedCards } from "../components/listings/FeaturedCards";
import { OutbidTicker } from "../components/listings/OutbidTicker";
import { ProjectTable } from "../components/listings/ProjectTable";
import { MarketOverview } from "../components/sidebar/MarketOverview";
import { RankList } from "../components/sidebar/RankList";
import { HowItWorks } from "../components/sidebar/HowItWorks";
import { PayWithCrypto } from "../components/sidebar/PayWithCrypto";
import { OutbidDialog } from "../components/listings/OutbidDialog";

export function HomePage() {
  const { projects, events, outbid } = useDirectory();
  const [category, setCategory] = useState<"all" | CategoryId>("all");
  const [url, setUrl] = useState("");
  const [heroCategory, setHeroCategory] = useState<CategoryId>("defi");
  const [dialogOpen, setDialogOpen] = useState(false);
  const topBid = (projects[0]?.bidUsd ?? 17005) + 1;

  function openDesk() {
    setDialogOpen(true);
  }

  return (
    <div className="mx-auto flex max-w-[1280px] flex-col gap-10 px-4 py-8 sm:px-6">
      <Hero
        topBid={topBid}
        url={url}
        category={heroCategory}
        onUrl={setUrl}
        onCategory={setHeroCategory}
        onOutbid={openDesk}
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-6">
          <FeaturedCards projects={projects} />
          <OutbidTicker events={events} />
          <ProjectTable projects={projects} category={category} onCategory={setCategory} />
        </div>
        <aside className="flex flex-col gap-4 xl:sticky xl:top-24 xl:self-start">
          <MarketOverview />
          <RankList title="Top Networks" kind="networks" />
          <RankList title="Top Categories" kind="categories" />
          <HowItWorks onList={openDesk} />
          <PayWithCrypto />
        </aside>
      </div>
      <OutbidDialog
        open={dialogOpen}
        defaultAmount={topBid}
        onClose={() => setDialogOpen(false)}
        onSubmit={(input) => {
          outbid({ ...input, url: input.url || url, category: input.category || heroCategory });
          setDialogOpen(false);
        }}
      />
    </div>
  );
}
