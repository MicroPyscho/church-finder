import { create } from "zustand";

interface Filters {
  price_min: number|null; price_max: number|null;
  listing_type: string; features: string[];
  counties: string[]; is_listed: boolean|null;
  min_ai_score: number|null; show_pre_market: boolean; intent: string;
}

interface S {
  query: string; results: any|null; intent: any|null;
  filters: Filters; page: number; sortBy: string;
  setQuery:   (q:string) => void;
  setResults: (r:any)    => void;
  setIntent:  (i:any)    => void;
  setFilters: (f:Partial<Filters>) => void;
  setPage:    (p:number) => void;
  setSortBy:  (s:string) => void;
  reset:      () => void;
}

const D: Filters = { price_min:null, price_max:null, listing_type:"any", features:[], counties:[], is_listed:null, min_ai_score:null, show_pre_market:false, intent:"" };

export const useSearchStore = create<S>((set) => ({
  query:"", results:null, intent:null, filters:D, page:1, sortBy:"relevance",
  setQuery:   (query)   => set({ query }),
  setResults: (results) => set({ results }),
  setIntent:  (intent)  => set({ intent }),
  setFilters: (f)       => set(s => ({ filters:{ ...s.filters, ...f } })),
  setPage:    (page)    => set({ page }),
  setSortBy:  (sortBy)  => set({ sortBy }),
  reset:      ()        => set({ query:"", results:null, intent:null, filters:D, page:1 }),
}));
