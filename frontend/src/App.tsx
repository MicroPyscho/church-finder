import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Heart, Bell, User, Sun, Moon } from "lucide-react";
import SearchPage     from "./pages/SearchPage";
import ResultsPage    from "./pages/ResultsPage";
import PropertyPage   from "./pages/PropertyPage";
import FavouritesPage from "./pages/FavouritesPage";
import AlertsPage     from "./pages/AlertsPage";
import AuthPage       from "./pages/AuthPage";
import ConfirmPage    from "./pages/ConfirmPage";
import AccountPage    from "./pages/AccountPage";
import LocationPage   from "./pages/LocationPage";
import AuthGateModal  from "./components/ui/AuthGateModal";
import { useAuthStore } from "./stores/authStore";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1 } } });

function Nav({ dark }: { dark: boolean }) {
  const nav = useNavigate();
  const { isLoggedIn, user, logout } = useAuthStore();
  return (
    <nav className="nav">
      <div className="wrap nav-inner">
        <button className="nav-logo" onClick={() => nav("/")}
          style={{ padding:0, background:"none", border:"none", cursor:"pointer" }}>
          <img
            src={dark ? "/nave-logo-white.svg" : "/nave-logo-black.svg"}
            alt="Nave"
            style={{ height:28, display:"block" }}
            onError={e => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        </button>
        <div className="nav-links">
          <NavLink to="/"           className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>Search</NavLink>
          <NavLink to="/favourites" className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>Saved</NavLink>
          <NavLink to="/alerts"     className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>Alerts</NavLink>
        </div>
        <div className="nav-right">
          <NavLink to="/favourites" className="btn-sm" style={{ border:"none" }}><Heart size={15}/></NavLink>
          <NavLink to="/alerts"     className="btn-sm" style={{ border:"none" }}><Bell  size={15}/></NavLink>
          {isLoggedIn && user
            ? <button className="btn-sm" onClick={logout} style={{ color:"var(--mid)" }}>
                <User size={13}/> {user.name.split(" ")[0]}
              </button>
            : <NavLink to="/account" className="btn-sm"><User size={13}/> Account</NavLink>
          }
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  const [dark, setDark] = useState(() =>
    localStorage.getItem("sanctuary_theme") === "dark"
  );

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("sanctuary_theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Nav dark={dark} />
        <div className="page">
          <button
            onClick={() => setDark(d => !d)}
            style={{
              position:"fixed", bottom:20, right:20,
              display:"flex", alignItems:"center", gap:6,
              background:"var(--white)", border:"1px solid var(--rule)",
              borderRadius:100, padding:"6px 12px 6px 10px",
              cursor:"pointer", color:"var(--mid)",
              fontSize:"0.76rem", fontFamily:"var(--font-body)",
              boxShadow:"0 2px 8px rgba(0,0,0,0.08)", zIndex:50,
            }}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? <Sun size={13}/> : <Moon size={13}/>}
            {dark ? "Light" : "Dark"}
          </button>
          <Routes>
            <Route path="/"                       element={<SearchPage />} />
            <Route path="/results"                element={<ResultsPage />} />
            <Route path="/properties/:id"         element={<PropertyPage />} />
            <Route path="/favourites"             element={<FavouritesPage />} />
            <Route path="/alerts"                 element={<AlertsPage />} />
            <Route path="/auth"                   element={<AuthPage />} />
            <Route path="/confirmed"              element={<ConfirmPage />} />
            <Route path="/account"                element={<AccountPage />} />
            <Route path="/churches-for-sale"      element={<LocationPage />} />
            <Route path="/churches-for-sale/:region" element={<LocationPage />} />
          </Routes>
        </div>
        <AuthGateModal />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
