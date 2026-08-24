import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Header } from "./components/layout/Header";
import { SearchDialog } from "./components/layout/SearchDialog";
import { CoinPage } from "./pages/CoinPage";
import { MarketsPage } from "./pages/MarketsPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { WatchlistPage } from "./pages/WatchlistPage";

export default function App() {
  const [searchOpen, setSearchOpen] = useState(false);
  const openSearch = useCallback(() => setSearchOpen(true), []);
  const closeSearch = useCallback(() => setSearchOpen(false), []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "/") return;
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        return;
      }
      event.preventDefault();
      setSearchOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="relative min-h-screen">
      <div className="desk-grid pointer-events-none absolute inset-0" />
      <Header onSearch={openSearch} />
      <main className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
        <Routes>
          <Route path="/" element={<MarketsPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/coin/:id" element={<CoinPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="relative mx-auto max-w-7xl px-4 pb-10 text-xs uppercase tracking-[0.16em] text-mute sm:px-6">
        Krypto · local-first desk · prices via CoinGecko
      </footer>
      <SearchDialog open={searchOpen} onClose={closeSearch} />
    </div>
  );
}
