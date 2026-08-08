import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, NavLink, useNavigate, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Heart, Bell, User, Sun, Moon, Menu, X } from "lucide-react";
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

function Nav({ dark, setDark }: { dark: boolean; setDark: (d: boolean) => void }) {
  const nav = useNavigate();
  const location = useLocation();
  const { isLoggedIn, user, logout } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close menu on route change
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  const NAV_LINKS = [
    { to: "/",                label: "Search"  },
    { to: "/churches-for-sale", label: "Regions" },
    { to: "/favourites",      label: "Saved"   },
    { to: "/alerts",          label: "Alerts"  },
  ];

  return (
    <>
      <nav className="nav">
        <div className="wrap nav-inner">
          {/* Logo */}
          <button className="nav-logo" onClick={() => nav("/")}
            style={{ padding:0, background:"none", border:"none", cursor:"pointer" }}>
            <img
              src={dark ? "/nave-logo-white.svg" : "/nave-logo-black.svg"}
              alt="Nave"
              style={{ height:"clamp(18px,3vw,24px)", width:"auto", maxWidth:"clamp(80px,12vw,110px)", display:"block" }}
              onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          </button>

          {/* Desktop nav links */}
          <div className="nav-links">
            {NAV_LINKS.map(l => (
              <NavLink key={l.to} to={l.to} end={l.to === "/"}
                className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
                {l.label}
              </NavLink>
            ))}
          </div>

          {/* Right side */}
          <div className="nav-right">
            {/* Dark mode toggle — in nav */}
            <button
              onClick={() => setDark(!dark)}
              title={dark ? "Light mode" : "Dark mode"}
              style={{
                width:30, height:30, borderRadius:"50%",
                border:"1px solid var(--line)", background:"var(--surface)",
                display:"flex", alignItems:"center", justifyContent:"center",
                cursor:"pointer", color:"var(--ink)", padding:0, flexShrink:0,
              }}
            >
              {dark ? <Sun size={13}/> : <Moon size={13}/>}
            </button>

            {/* Desktop: heart + bell + account */}
            <NavLink to="/favourites" className="btn-sm nav-desktop-only" style={{ border:"none" }}>
              <Heart size={15}/>
            </NavLink>
            <NavLink to="/alerts" className="btn-sm nav-desktop-only" style={{ border:"none" }}>
              <Bell size={15}/>
            </NavLink>
            {isLoggedIn && user
              ? <button className="btn-sm nav-desktop-only" onClick={logout} style={{ color:"var(--mid)" }}>
                  <User size={13}/> {user.name.split(" ")[0]}
                </button>
              : <NavLink to="/account" className="btn-sm nav-desktop-only">
                  <User size={13}/> Account
                </NavLink>
            }

            {/* Mobile hamburger */}
            <button
              className="nav-mobile-only"
              onClick={() => setMenuOpen(o => !o)}
              style={{ width:30, height:30, borderRadius:"50%", border:"1px solid var(--line)", background:"var(--surface)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", color:"var(--ink)", padding:0 }}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
            >
              {menuOpen ? <X size={15}/> : <Menu size={15}/>}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile dropdown menu */}
      {menuOpen && (
        <div style={{
          position:"fixed", top:52, left:0, right:0, zIndex:190,
          background:"var(--surface)", borderBottom:"1px solid var(--line)",
          boxShadow:"0 8px 32px rgba(0,0,0,0.1)",
          animation:"slide-up 0.15s ease",
          padding:"8px 0 16px",
        }}>
          {NAV_LINKS.map(l => (
            <NavLink key={l.to} to={l.to} end={l.to === "/"}
              onClick={() => setMenuOpen(false)}
              style={({ isActive }) => ({
                display:"block", padding:"12px 22px",
                fontSize:"0.95rem", fontWeight: isActive ? 600 : 400,
                color: isActive ? "var(--ink)" : "var(--ink2)",
                textDecoration:"none", borderLeft: isActive ? "3px solid var(--violet)" : "3px solid transparent",
                background: isActive ? "var(--surface2)" : "transparent",
                transition:"all .15s",
              })}
            >
              {l.label}
            </NavLink>
          ))}
          <div style={{ borderTop:"1px solid var(--line)", margin:"8px 0", padding:"8px 22px 0" }}>
            <NavLink to="/favourites" onClick={() => setMenuOpen(false)}
              style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 0", fontSize:"0.88rem", color:"var(--ink2)", textDecoration:"none" }}>
              <Heart size={14}/> Saved properties
            </NavLink>
            <NavLink to="/alerts" onClick={() => setMenuOpen(false)}
              style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 0", fontSize:"0.88rem", color:"var(--ink2)", textDecoration:"none" }}>
              <Bell size={14}/> Alerts
            </NavLink>
            {isLoggedIn && user
              ? <button onClick={() => { logout(); setMenuOpen(false); }}
                  style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 0", fontSize:"0.88rem", color:"var(--mid)", background:"none", border:"none", cursor:"pointer", width:"100%" }}>
                  <User size={14}/> Sign out ({user.name.split(" ")[0]})
                </button>
              : <NavLink to="/account" onClick={() => setMenuOpen(false)}
                  style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 0", fontSize:"0.88rem", color:"var(--ink2)", textDecoration:"none" }}>
                  <User size={14}/> Account
                </NavLink>
            }
          </div>
        </div>
      )}
    </>
  );
}

function Footer({ dark }: { dark: boolean }) {
  return (
    <footer style={{ borderTop:"1px solid var(--line)", background:"var(--bg)" }}>
      <div style={{ maxWidth:1040, margin:"0 auto", padding:"30px 22px", display:"flex", alignItems:"center", justifyContent:"space-between", gap:16, flexWrap:"wrap" }}>
        <img
          src={dark ? "/nave-logo-white.svg" : "/nave-logo-black.svg"}
          alt="Nave"
          style={{ height:15, width:"auto", display:"block", opacity:0.5 }}
          onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
        <p style={{ font:"400 12px 'Space Grotesk'", color:"var(--ink4)", margin:0, textAlign:"center" }}>
          © 2026 Nave · Church &amp; Gathering Space Intelligence · UK hosted · GDPR compliant
        </p>
        <div style={{ display:"flex", gap:16, alignItems:"center" }}>
          <NavLink to="/churches-for-sale" style={{ font:"400 12px 'Space Grotesk'", color:"var(--ink3)", textDecoration:"none" }}>Regions</NavLink>
          <NavLink to="/alerts"            style={{ font:"400 12px 'Space Grotesk'", color:"var(--ink3)", textDecoration:"none" }}>Alerts</NavLink>
          <NavLink to="/account"           style={{ font:"400 12px 'Space Grotesk'", color:"var(--ink3)", textDecoration:"none" }}>Account</NavLink>
        </div>
      </div>
    </footer>
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
        <Nav dark={dark} setDark={setDark} />
        <div className="page">
          <Routes>
            <Route path="/"                          element={<SearchPage />} />
            <Route path="/results"                   element={<ResultsPage />} />
            <Route path="/properties/:id"            element={<PropertyPage />} />
            <Route path="/favourites"                element={<FavouritesPage />} />
            <Route path="/alerts"                    element={<AlertsPage />} />
            <Route path="/auth"                      element={<AuthPage />} />
            <Route path="/confirmed"                 element={<ConfirmPage />} />
            <Route path="/account"                   element={<AccountPage />} />
            <Route path="/churches-for-sale"         element={<LocationPage />} />
            <Route path="/churches-for-sale/:region" element={<LocationPage />} />
          </Routes>
        </div>
        <Footer dark={dark} />
        <AuthGateModal />
      </BrowserRouter>
    </QueryClientProvider>
  );
}