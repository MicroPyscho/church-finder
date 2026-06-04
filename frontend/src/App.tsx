import { BrowserRouter, Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Heart, Bell, User } from "lucide-react";
import SearchPage     from "./pages/SearchPage";
import ResultsPage    from "./pages/ResultsPage";
import PropertyPage   from "./pages/PropertyPage";
import FavouritesPage from "./pages/FavouritesPage";
import AlertsPage     from "./pages/AlertsPage";
import AuthPage       from "./pages/AuthPage";
import ConfirmPage    from "./pages/ConfirmPage";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1 } } });

function Nav() {
  const nav = useNavigate();
  return (
    <nav className="nav">
      <div className="wrap nav-inner">
        <button className="nav-logo" onClick={() => nav("/")}>Sanctuary</button>
        <div className="nav-links">
          <NavLink to="/"           end       className={({isActive}) => `nav-link${isActive?" active":""}`}>Search</NavLink>
          <NavLink to="/favourites"           className={({isActive}) => `nav-link${isActive?" active":""}`}>Saved</NavLink>
          <NavLink to="/alerts"               className={({isActive}) => `nav-link${isActive?" active":""}`}>Alerts</NavLink>
        </div>
        <div className="nav-right">
          <NavLink to="/favourites" className="btn-sm" style={{border:"none"}}><Heart size={15}/></NavLink>
          <NavLink to="/alerts"     className="btn-sm" style={{border:"none"}}><Bell  size={15}/></NavLink>
          <NavLink to="/auth"       className="btn-sm"><User size={13}/> Sign in</NavLink>
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Nav />
        <div className="page">
          <Routes>
            <Route path="/"               element={<SearchPage />} />
            <Route path="/results"        element={<ResultsPage />} />
            <Route path="/properties/:id" element={<PropertyPage />} />
            <Route path="/favourites"     element={<FavouritesPage />} />
            <Route path="/alerts"         element={<AlertsPage />} />
            <Route path="/auth"           element={<AuthPage />} />
            <Route path="/confirmed"      element={<ConfirmPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
