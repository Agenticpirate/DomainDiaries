import { Navigate, Route, Routes } from "react-router-dom";
import { useState } from "react";
import { DirectoryProvider } from "./context/DirectoryContext";
import { Header } from "./components/layout/Header";
import { Footer } from "./components/layout/Footer";
import { HomePage } from "./pages/HomePage";
import { NetworksPage } from "./pages/NetworksPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { PromotePage } from "./pages/PromotePage";
import { AboutPage } from "./pages/AboutPage";
import { ResourcesPage } from "./pages/ResourcesPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ListingGate } from "./components/listings/ListingGate";

export default function App() {
  const [listOpen, setListOpen] = useState(false);
  return (
    <DirectoryProvider>
      <Header onList={() => setListOpen(true)} />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/networks" element={<NetworksPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/promote" element={<PromotePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/resources" element={<ResourcesPage />} />
          <Route path="/project/:id" element={<ProjectPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <Footer />
      <ListingGate open={listOpen} onClose={() => setListOpen(false)} />
    </DirectoryProvider>
  );
}
