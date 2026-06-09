import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Search, Mic, MicOff, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "../api/client";
import { useSearchStore } from "../stores/searchStore";
import FollowUpFlow from "../components/search/FollowUpFlow";
import EdgeCase from "../components/search/EdgeCase";

const EXAMPLES = [
  "Affordable churches under £100k with parking in Kent",
  "Former Methodist chapel with hall, Yorkshire",
  "Listed church to convert, South East, under £500k",
  "Community hall with graveyard, auction only",
  "Large gathering space with high ceilings, London",
  "Church with development potential, Devon",
];

const MAX_VISIBLE_CHARS = 120;

export default function SearchPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const { setResults, setQuery, setIntent, query: storedQuery } = useSearchStore();

  const [q,            setQ]            = useState(storedQuery || "");
  const [recording, setRecording] = useState(false);
  const voiceSupported = typeof window !== "undefined" && !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  const voiceSupported = !!(window.SpeechRecognition || (window as any).webkitSpeechRecognition);
  const [edgeCase,     setEdgeCase]     = useState<any>(null);
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [localIntent,  setLocalIntent]  = useState<any>(null);
  const [searchData,   setSearchData]   = useState<any>(null);
  const [focused,      setFocused]      = useState(false);
  const [expanded,     setExpanded]     = useState(false);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 160) + "px";
    }
  }, [q]);

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
    const trimmed = str.trim();
    if (!trimmed) return;
    setEdgeCase(null);
    setShowFollowUp(false);
    mut.mutate(trimmed);
  }

  function handleVoice() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    // If already recording, stop
    if (recording && recognitionRef.current) {
      recognitionRef.current.stop();
      return;
    }

    const r = new SR();
    r.lang = "en-GB";
    r.continuous = true;          // keep listening until stopped
    r.interimResults = true;      // show partial results as user speaks
    r.maxAlternatives = 1;

    let finalTranscript = q;      // preserve existing text

    r.onstart = () => {
      setRecording(true);
    };

    r.onresult = (e: any) => {
      let interim = "";
      let final = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const transcript = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }
      if (final) {
        finalTranscript = (finalTranscript + " " + final).trim();
      }
      // Show interim results immediately as user speaks
      setQ((finalTranscript + (interim ? " " + interim : "")).trim());
    };

    r.onend = () => {
      setRecording(false);
      recognitionRef.current = null;
      // Auto-search if we captured something new
      const captured = finalTranscript.trim();
      if (captured && captured !== (storedQuery || "").trim()) {
        setQ(captured);
        setTimeout(() => search(captured), 200);
      }
    };

    r.onerror = (e: any) => {
      setRecording(false);
      recognitionRef.current = null;
      if (e.error !== "no-speech" && e.error !== "aborted") {
        console.warn("Voice error:", e.error);
      }
    };

    recognitionRef.current = r;
    r.start();
  }

  function handleFollowUpDone(filters: any) {
    useSearchStore.getState().setFilters(filters);
    navigate("/results");
  }

  const showExamples = !q.trim() && !showFollowUp && !edgeCase && !focused;
  const isLong = q.length > MAX_VISIBLE_CHARS;

  return (
    <div className="search-hero">
      <p className="search-hero__eyebrow">UK Church &amp; Gathering Space Finder</p>
      <h1 className="search-hero__title">Find your next<br /><em>sacred space</em></h1>

      {!showFollowUp && !edgeCase && (
        <p className="search-hero__sub">
          Describe exactly what you need. We search 30+ sources simultaneously.
        </p>
      )}

      <div className="searchbar-wrap">
        <div className={`searchbar searchbar--textarea${recording ? " searchbar--recording" : ""}`}>

          {/* Textarea instead of input — auto-expands */}
          <textarea
            ref={inputRef}
            className="searchbar__input"
            placeholder="e.g. affordable church with parking, under £150k in Yorkshire…"
            value={q}
            rows={1}
            onChange={e => {
              setQ(e.target.value);
              setExpanded(false);
            }}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                search();
              }
            }}
            style={{
              resize: "none",
              overflow: "hidden",
              minHeight: 36,
              maxHeight: 160,
              lineHeight: "1.5",
            }}
          />

          <div className="searchbar__actions">
            {/* Voice button */}
            <button
              className={`btn-voice${recording ? " recording" : ""}`}
              onClick={handleVoice}
              title={recording ? "Stop recording" : "Voice search"}
              type="button"
            >
              {recording
                ? <MicOff size={15} color="#e53e3e" />
                : <Mic size={15} />
              }
            </button>

            {/* Search button — always enabled if there's text */}
            <button
              className="btn-search"
              onClick={() => search()}
              disabled={!q.trim()}
              type="button"
            >
              {mut.isPending
                ? <span className="spin" style={{ fontSize: "1rem" }}>◌</span>
                : <><Search size={13} /> Search</>
              }
            </button>
          </div>
        </div>

        {/* Recording indicator */}
        {recording && (
          <div style={{
            fontSize: "0.72rem", color: "#e53e3e",
            marginTop: 6, display: "flex", alignItems: "center", gap: 6
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: "#e53e3e", display: "inline-block",
              animation: "pulse 1s infinite"
            }} />
            Listening… tap mic to stop
          </div>
        )}

        {/* Follow-up flow */}
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

        {/* Examples */}
        {showExamples && (
          <div className="examples">
            {EXAMPLES.map(ex => (
              <button
                key={ex}
                className="example"
                type="button"
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
