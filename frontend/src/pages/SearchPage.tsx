import { useSEO } from "../hooks/useSEO";
import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Search, Mic, MicOff, Clock, X } from "lucide-react";
import { api } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import { useAuthStore } from "../stores/authStore";
import FollowUpFlow from "../components/search/FollowUpFlow";
import EdgeCase from "../components/search/EdgeCase";

const FALLBACK_EXAMPLES = [
  "Affordable churches under £100k with parking in Kent",
  "Former Methodist chapel with hall, Yorkshire",
  "Listed church to convert, South East, under £500k",
  "Community hall with graveyard, auction only",
  "Large gathering space with high ceilings, London",
  "Church with development potential, Devon",
];

const MAX_RECENT = 5;

function getStorageKey(userId?: string) {
  return userId ? `nave_recent_searches_${userId}` : "nave_recent_searches_guest";
}
function loadRecentSearches(userId?: string): string[] {
  try { const raw = localStorage.getItem(getStorageKey(userId)); return raw ? JSON.parse(raw) : []; } catch { return []; }
}
function saveRecentSearch(query: string, userId?: string) {
  try {
    const key = getStorageKey(userId);
    const existing = loadRecentSearches(userId);
    const updated = [query, ...existing.filter(q => q !== query)].slice(0, MAX_RECENT);
    localStorage.setItem(key, JSON.stringify(updated));
  } catch {}
}
function clearRecentSearches(userId?: string) {
  try { localStorage.removeItem(getStorageKey(userId)); } catch {}
}

export default function SearchPage() {
  useSEO({
    title: "Nave",
    description: "Search 100+ churches, chapels and places of worship for sale across the UK. Find your perfect ecclesiastical property.",
  });
  const navigate = useNavigate();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { setResults, setQuery, setIntent, query: storedQuery } = useSearchStore();
  const { user } = useAuthStore();

  const [q,            setQ]            = useState(storedQuery || "");
  const [recording,    setRecording]    = useState(false);
  const [edgeCase,     setEdgeCase]     = useState<any>(null);
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [localIntent,  setLocalIntent]  = useState<any>(null);
  const [searchData,   setSearchData]   = useState<any>(null);
  const [focused,      setFocused]      = useState(false);
  const [expanded,     setExpanded]     = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [suggestion,   setSuggestion]   = useState("");

  useEffect(() => { setRecentSearches(loadRecentSearches(user?.id?.toString())); }, [user?.id]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 160) + "px";
    }
  }, [q]);

  useEffect(() => {
    if (q.trim().length < 2) { setSuggestion(""); return; }
    const match = recentSearches.find(s => s.toLowerCase().startsWith(q.toLowerCase()) && s.toLowerCase() !== q.toLowerCase());
    setSuggestion(match ? match.slice(q.length) : "");
  }, [q, recentSearches]);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setShowDropdown(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const mut = useMutation({
    mutationFn: (query: string) =>
      api.post("/api/search", { query, filters: {}, page: 1 }).then(r => r.data),
    onSuccess: (data) => {
      if (data.is_relevant_query === false) { setEdgeCase(data); return; }
      setLocalIntent(data.intent);
      setSearchData(data);
      setShowFollowUp(!!data.follow_up_questions?.length);
      setIntent(data.intent);
      setResults(data);
      setQuery(q);
      if (!data.follow_up_questions?.length) navigate("/results");
    },
  });

  const buttonState =
    recording     ? "recording" :
    mut.isPending ? "searching" :
    showFollowUp  ? "follow_up" :
    q.trim()      ? "typing"    : "idle";

  const BUTTON_CONFIG = {
    idle:      { label: "Search",    hint: "Type or speak your query" },
    typing:    { label: "Search",    hint: "Press Enter or click Search" },
    recording: { label: "Stop",      hint: "Tap to stop recording" },
    searching: { label: "Searching", hint: "Finding properties..." },
    follow_up: { label: "Continue",  hint: "Answer above to refine results" },
  } as const;
  const btn = BUTTON_CONFIG[buttonState as keyof typeof BUTTON_CONFIG];

  function search(str = q) {
    const trimmed = str.trim();
    if (!trimmed) return;
    setEdgeCase(null); setShowFollowUp(false); setShowDropdown(false); setSuggestion("");
    saveRecentSearch(trimmed, user?.id?.toString());
    setRecentSearches(loadRecentSearches(user?.id?.toString()));
    // Track search event
    (window as any).umami?.track("search", { query: trimmed });
    mut.mutate(trimmed);
  }

  function handleVoice() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    if (recording && recognitionRef.current) { recognitionRef.current.stop(); return; }
    const r = new SR();
    r.lang = "en-GB"; r.continuous = true; r.interimResults = true; r.maxAlternatives = 1;
    let finalTranscript = q;
    r.onstart  = () => setRecording(true);
    r.onresult = (e: any) => {
      let interim = "", final = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t; else interim += t;
      }
      if (final) finalTranscript = (finalTranscript + " " + final).trim();
      setQ((finalTranscript + (interim ? " " + interim : "")).trim());
    };
    r.onend = () => {
      setRecording(false); recognitionRef.current = null;
      const captured = finalTranscript.trim();
      if (captured && captured !== (storedQuery || "").trim()) { setQ(captured); setTimeout(() => search(captured), 200); }
    };
    r.onerror = (e: any) => {
      setRecording(false); recognitionRef.current = null;
      if (e.error !== "no-speech" && e.error !== "aborted") console.warn("Voice error:", e.error);
    };
    recognitionRef.current = r; r.start();
  }

  function handleFollowUpDone(filters: any) {
    useSearchStore.getState().setFilters(filters);
    navigate("/results");
  }

  function acceptSuggestion() {
    if (suggestion) { setQ(q + suggestion); setSuggestion(""); }
  }

  const showRecentDropdown = focused && !q.trim() && recentSearches.length > 0 && !showFollowUp && !edgeCase;
  const showExamples = !q.trim() && !showFollowUp && !edgeCase && !focused && recentSearches.length === 0;

  return (
    <div className="search-hero">

      {/* ── Eyebrow: UK Jack shield + label ── */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:9, margin:"0 0 18px" }}>
        <svg width="20" height="24" viewBox="0 0 24 28" fill="none" xmlns="http://www.w3.org/2000/svg"
          style={{ filter:"drop-shadow(0 1px 1.5px rgba(0,0,0,0.22))", flexShrink:0 }} aria-hidden="true">
          <defs>
            <clipPath id="njShield">
              <path d="M2 3.2 Q2 2 3.2 2 H20.8 Q22 2 22 3.2 V14.5 C22 21.5 12 26 12 26 C12 26 2 21.5 2 14.5 Z"/>
            </clipPath>
            <linearGradient id="njEmboss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0"    stopColor="#ffffff" stopOpacity="0.4"/>
              <stop offset="0.45" stopColor="#ffffff" stopOpacity="0"/>
              <stop offset="1"    stopColor="#000000" stopOpacity="0.28"/>
            </linearGradient>
          </defs>
          <g clipPath="url(#njShield)">
            <rect x="0" y="0" width="24" height="28" fill="#012169"/>
            <path d="M0 0 L24 28 M24 0 L0 28" stroke="#ffffff" strokeWidth="5"/>
            <path d="M0 0 L24 28 M24 0 L0 28" stroke="#C8102E" strokeWidth="2"/>
            <path d="M12 0 V28 M0 14 H24" stroke="#ffffff" strokeWidth="7"/>
            <path d="M12 0 V28 M0 14 H24" stroke="#C8102E" strokeWidth="3.6"/>
            <rect x="0" y="0" width="24" height="28" fill="url(#njEmboss)"/>
          </g>
          <path d="M2 3.2 Q2 2 3.2 2 H20.8 Q22 2 22 3.2 V14.5 C22 21.5 12 26 12 26 C12 26 2 21.5 2 14.5 Z"
            fill="none" stroke="rgba(0,0,0,0.2)" strokeWidth="1"/>
        </svg>
        <span style={{ fontFamily:"'Gabarito'", fontWeight:700, fontSize:13, letterSpacing:"0.14em", textTransform:"uppercase", color:"var(--ink2)", whiteSpace:"nowrap" }}>
          UK's dedicated search
        </span>
      </div>

      {/* ── Hero title ── */}
      <h1 style={{
        fontFamily:"'Gabarito'", fontWeight:900,
        fontSize:"clamp(40px, 6.6vw, 76px)",
        lineHeight:1.0, letterSpacing:"-0.045em",
        color:"var(--ink)", margin:"0 0 32px",
        textAlign:"center",
      }}>
        <span style={{ display:"block" }}>
          <em style={{
            fontFamily:"'League Script', cursive", fontStyle:"normal", fontWeight:400,
            WebkitTextStroke:"0.7px #6b70c2", fontSize:"0.52em", color:"#6b70c2",
            verticalAlign:"0.1em", marginRight:"0.16em",
          }}>for</em>churches, chapels
        </span>
        <span style={{ display:"block" }}>
          <em style={{
            fontFamily:"'League Script', cursive", fontStyle:"normal", fontWeight:400,
            WebkitTextStroke:"0.7px #6b70c2", fontSize:"0.6em", color:"#6b70c2",
            marginRight:"0.12em", verticalAlign:"0.02em",
          }}>and</em>places of worship
        </span>
      </h1>

      {!showFollowUp && !edgeCase && (
        <p className="search-hero__sub">
          Describe your search. See results from 30+ sources.
        </p>
      )}

      <div className="searchbar-wrap" ref={dropdownRef}>
        <div className={`searchbar searchbar--textarea${recording ? " searchbar--recording" : ""}`} style={{ position:"relative" }}>

          {suggestion && (
            <div style={{ position:"absolute", left:"clamp(12px,2.5vw,22px)", top:"50%", transform:"translateY(-50%)", pointerEvents:"none", fontSize:"clamp(0.78rem,2vw,0.95rem)", whiteSpace:"nowrap", overflow:"hidden" }}>
              <span style={{ color:"transparent" }}>{q}</span>
              <span style={{ color:"var(--mid)", opacity:0.5 }}>{suggestion}</span>
            </div>
          )}

          <textarea
            ref={inputRef}
            className="searchbar__input"
            placeholder={recentSearches.length > 0 ? "Search again or try something new…" : "e.g. churches under 250k for sale in London…"}
            value={q}
            rows={1}
            onChange={e => { setQ(e.target.value); setExpanded(false); setShowDropdown(false); }}
            onFocus={() => { setFocused(true); if (!q.trim() && recentSearches.length > 0) setShowDropdown(true); }}
            onBlur={() => { setFocused(false); setTimeout(() => setShowDropdown(false), 150); }}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); search(); }
              if (e.key === "Tab" && suggestion) { e.preventDefault(); acceptSuggestion(); }
              if (e.key === "ArrowRight" && suggestion && inputRef.current) {
                if (inputRef.current.selectionStart === q.length) { e.preventDefault(); acceptSuggestion(); }
              }
            }}
            style={{ resize:"none", overflow:"hidden", minHeight:8, maxHeight:45, lineHeight:"1.5", position:"relative", zIndex:1, background:"transparent" }}
          />

          <div className="searchbar__actions">
            <button className={`btn-voice${recording ? " recording" : ""}`} onClick={handleVoice} title={recording ? "Stop recording" : "Voice search"} type="button">
              {recording ? <MicOff size={15} color="#e53e3e" /> : <Mic size={15} />}
            </button>
            <div style={{ position:"relative", flexShrink:0, display:"inline-flex", borderRadius:14 }}>
              <div className="nave-halo-glow" />
              <div className="nave-halo-ring" />
              <button
                className={`btn-search btn-search--${buttonState}`}
                style={{ position:"relative", zIndex:1 }}
                onClick={() => {
                  if (buttonState === "recording") recognitionRef.current?.stop();
                  else if (buttonState === "follow_up") navigate("/results");
                  else search();
                }}
                disabled={buttonState === "searching" || buttonState === "idle"}
                title={btn.hint} type="button"
              >
                {buttonState === "searching" && <span className="spin">◌</span>}
                {buttonState === "recording" && <MicOff size={13} />}
                {buttonState === "follow_up" && <span>→</span>}
                {(buttonState === "idle" || buttonState === "typing") && <Search size={13} />}
                {" "}{btn.label}
              </button>
            </div>
          </div>
        </div>

        {/* Recent searches dropdown */}
        {showRecentDropdown && (
          <div style={{ position:"absolute", left:0, right:0, marginTop:6, background:"var(--white)", border:"1px solid var(--rule)", borderRadius:16, boxShadow:"0 8px 32px rgba(0,0,0,0.1)", zIndex:100, overflow:"hidden", animation:"slide-up 0.15s ease" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"10px 14px 6px", borderBottom:"1px solid var(--rule-soft)" }}>
              <span style={{ fontSize:"0.68rem", fontWeight:600, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--mid)" }}>Recent searches</span>
              <button onClick={() => { clearRecentSearches(user?.id?.toString()); setRecentSearches([]); setShowDropdown(false); }} style={{ fontSize:"0.68rem", color:"var(--mid)", background:"none", border:"none", cursor:"pointer", padding:"2px 4px" }}>Clear</button>
            </div>
            {recentSearches.map((s, i) => (
              <button key={i} onMouseDown={() => { setQ(s); setShowDropdown(false); setTimeout(() => search(s), 50); }}
                style={{ display:"flex", alignItems:"center", gap:10, width:"100%", padding:"10px 14px", background:"none", border:"none", textAlign:"left", cursor:"pointer", fontSize:"0.85rem", color:"var(--ink)", borderBottom: i < recentSearches.length-1 ? "1px solid var(--rule-soft)" : "none", transition:"background 0.1s" }}
                onMouseEnter={e => (e.currentTarget.style.background="var(--off-white)")}
                onMouseLeave={e => (e.currentTarget.style.background="none")}
              >
                <Clock size={13} style={{ color:"var(--mid)", flexShrink:0 }} />
                <span style={{ flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{s}</span>
                <X size={11} style={{ color:"var(--mid)", flexShrink:0, opacity:0.5 }} />
              </button>
            ))}
          </div>
        )}

        {recording && (
          <div style={{ fontSize:"0.72rem", color:"#e53e3e", marginTop:6, display:"flex", alignItems:"center", gap:6 }}>
            <span style={{ width:8, height:8, borderRadius:"50%", background:"#e53e3e", display:"inline-block", animation:"pulse 1s infinite" }} />
            Listening… tap mic to stop
          </div>
        )}

        {showFollowUp && localIntent && !edgeCase && (
          <FollowUpFlow intent={localIntent} questions={searchData?.follow_up_questions ?? []} onComplete={handleFollowUpDone} onSkip={() => navigate("/results")} />
        )}

        {edgeCase && (
          <EdgeCase data={edgeCase} onSuggestionClick={s => { setEdgeCase(null); setQ(s); search(s); }} />
        )}

        {showExamples && (
          <div className="examples">
            {FALLBACK_EXAMPLES.map(ex => (
              <button key={ex} className="example" type="button" onClick={() => { setQ(ex); inputRef.current?.focus(); }}>{ex}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}