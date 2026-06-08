import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Search, Mic, MicOff } from "lucide-react";
import { api } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import FollowUpFlow from "../components/search/FollowUpFlow";
import EdgeCase     from "../components/search/EdgeCase";

const EXAMPLES = [
  "Affordable churches under £100k with parking in Kent",
  "Former Methodist chapel with hall, Yorkshire",
  "Listed church to convert, South East, under £500k",
  "Community hall with graveyard, auction only",
  "Large gathering space with high ceilings, London",
  "Church with development potential, Devon",
];

export default function SearchPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const { setResults, setQuery, setIntent, query: storedQuery } = useSearchStore();

  const [q,            setQ]            = useState(storedQuery || "");
  const [recording,    setRecording]    = useState(false);
  const [edgeCase,     setEdgeCase]     = useState<any>(null);
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [localIntent,  setLocalIntent]  = useState<any>(null);
  const [searchData,   setSearchData]   = useState<any>(null);
  const [focused,      setFocused]      = useState(false);

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

  function search(str = q) {
    if (!str.trim()) return;
    setEdgeCase(null);
    setShowFollowUp(false);
    mut.mutate(str);
  }

  function handleVoice() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Voice search requires Chrome or Edge."); return; }
    const r = new SR();
    r.lang = "en-GB";
    r.onstart  = () => setRecording(true);
    r.onend    = () => setRecording(false);
    r.onresult = (e: any) => {
      const t = e.results[0][0].transcript;
      setQ(t);
      setTimeout(() => search(t), 200);
    };
    r.start();
  }

  function handleFollowUpDone(filters: any) {
    useSearchStore.getState().setFilters(filters);
    navigate("/results");
  }

  // Hide examples when: user has typed something, or follow-up is showing, or edge case
  const showExamples = !q.trim() && !showFollowUp && !edgeCase && !focused;

  return (
    <div className="search-hero">
      <p className="search-hero__eyebrow">UK Church &amp; Gathering Space Finder</p>
      <h1 className="search-hero__title">Find your next<br /><em>sacred space</em></h1>

      {/* Sub-text — hide when follow-up is showing to save space */}
      {!showFollowUp && !edgeCase && (
        <p className="search-hero__sub">
          Describe exactly what you need. We search 30+ sources simultaneously.
        </p>
      )}

      <div className="searchbar-wrap">
        <div className="searchbar">
          <input
            ref={inputRef}
            className="searchbar__input"
            placeholder="e.g. affordable church with parking, under £150k…"
            value={q}
            onChange={e => setQ(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={e => e.key === "Enter" && search()}
            autoFocus
          />
          <div className="searchbar__actions">
            <button
              className={`btn-voice${recording ? " recording" : ""}`}
              onClick={handleVoice}
              title="Voice search"
            >
              {recording ? <MicOff size={15} /> : <Mic size={15} />}
            </button>
            <button
              className="btn-search"
              onClick={() => search()}
              disabled={mut.isPending || !q.trim()}
            >
              {mut.isPending
                ? <span className="spin" style={{ fontSize: "1rem" }}>◌</span>
                : <><Search size={13} /> Search</>
              }
            </button>
          </div>
        </div>

        {/* Follow-up flow — appears directly below search bar */}
        {showFollowUp && localIntent && !edgeCase && (
          <FollowUpFlow
            intent={localIntent}
            questions={searchData?.follow_up_questions ?? []}
            onComplete={handleFollowUpDone}
            onSkip={() => navigate("/results")}
          />
        )}

        {/* Edge case */}
        {edgeCase && (
          <EdgeCase
            data={edgeCase}
            onSuggestionClick={s => { setEdgeCase(null); setQ(s); search(s); }}
          />
        )}

        {/* Examples — only show when idle */}
        {showExamples && (
          <div className="examples">
            {EXAMPLES.map(ex => (
              <button
                key={ex}
                className="example"
                onClick={() => { setQ(ex); inputRef.current?.focus(); }}
              >
                {ex}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
