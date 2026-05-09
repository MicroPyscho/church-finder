import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { useState } from "react";
import {
  Church, LayoutDashboard, Rocket, Activity, Menu, X,
} from "lucide-react";
import ListingsPage    from "./components/ListingsPage";
import DeploymentsPage from "./components/DeploymentsPage";
import CrawlRunsPage   from "./components/CrawlRunsPage";
import HealthBadge     from "./components/HealthBadge";
import EnvBanner       from "./components/EnvBanner";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime:  30_000,
      retry:      2,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-shell">
          <EnvBanner />

          <header className="topbar">
            <div className="topbar-left">
              <Church size={22} strokeWidth={1.5} />
              <span className="brand">ChurchFinder</span>
            </div>

            <nav className={`main-nav ${navOpen ? "open" : ""}`}>
              <NavLink to="/"            end onClick={() => setNavOpen(false)}>
                <LayoutDashboard size={15} /> Listings
              </NavLink>
              <NavLink to="/deployments"    onClick={() => setNavOpen(false)}>
                <Rocket size={15} /> Deployments
              </NavLink>
              <NavLink to="/crawl-runs"     onClick={() => setNavOpen(false)}>
                <Activity size={15} /> Crawl Runs
              </NavLink>
            </nav>

            <div className="topbar-right">
              <HealthBadge />
              <button
                className="nav-toggle"
                onClick={() => setNavOpen(o => !o)}
                aria-label="Toggle nav"
              >
                {navOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </header>

          <main className="page-content">
            <Routes>
              <Route path="/"            element={<ListingsPage />} />
              <Route path="/deployments" element={<DeploymentsPage />} />
              <Route path="/crawl-runs"  element={<CrawlRunsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
