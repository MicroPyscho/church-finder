# Ulouka.com — Product & Technical Documentation

**Prepared for:** Okereke Kelechi Collins
**Project:** Ulouka — UK church, chapel & gathering-space property finder
**Status:** Pre-launch (backend live on Railway, frontend deploying to Vercel)
**Date:** August 2026

> A note on sourcing: sections below are built directly from the architecture we've
> implemented together (FastAPI + Postgres on Railway, React/Vite frontend, APScheduler
> scraper pipeline, `alert-truth` worker) plus what you've told me about goals and the
> wider Sacred Spaces ecosystem. Anywhere I've had to assume something not yet
> discussed, it's marked **[ASSUMPTION — confirm]** so you can correct it rather than
> silently inheriting a guess.

---

## 1. Product Requirements Document (PRD)

### 1.1 Problem statement
Former churches, chapels, and religious gathering spaces come to market across dozens
of scattered sources — denominational property offices, regional auction houses,
mainstream portals, planning registers — with no single place to search them. Buyers,
developers, and communities interested in these buildings (residential conversion,
community reuse, commercial redevelopment) currently have to manually check many
sites. Ulouka aggregates these into one searchable, continuously updated database.

### 1.2 Target users
- **Property developers / investors** looking for conversion opportunities
- **Faith communities** seeking a new or additional worship space
- **Community organisations** looking for large character buildings (halls, event
  space, co-working, arts venues)
- **Individual buyers** drawn to distinctive architectural conversions
- **Researchers / journalists** tracking the trend of church closures and reuse

**[ASSUMPTION — confirm]** Primary persona ranked first for MVP: property developers/
investors, since they're the most likely to return regularly and value freshness/alerts.

### 1.3 Core value proposition
"One place to see every former church, chapel, and gathering space currently for sale
or lease in the UK — updated daily, deduplicated, and searchable by location, price,
and property type."

### 1.4 Success metrics (early stage)
- Weekly returning visitors
- Searches per session
- Listing click-through rate (site → source listing)
- Email/alert sign-ups (once built)
- Number of active, deduplicated listings in the database

### 1.5 Out of scope for now
- Direct enquiry/transaction handling (site links out to the original source)
- Paid placements or agent accounts
- International markets (UK-only)
- Rental-only or generic residential listings (site stays focused on the
  church/chapel/gathering-space niche)

---

## 2. Technical Requirements Document (TRD)

### 2.1 Architecture overview

```
┌─────────────────┐        ┌──────────────────────┐
│   Frontend        │       │   church-finder        │  ← FastAPI web service
│   (React + Vite)   │──────▶│   (Railway, Dockerfile) │
│   Vercel            │  API  │   /health /listings     │
│   ulouka.com        │       │   /api/search /api/*    │
└─────────────────┘        └───────────┬───────────┘
                                          │ reads/writes
                                          ▼
                                ┌──────────────────┐
                                │   Postgres          │  ← Railway plugin
                                └──────────────────┘
                                          ▲
                                          │ writes
                                ┌───────────────────┐
                                │   alert-truth        │  ← background worker
                                │   (Railway, Dockerfile)│
                                │   APScheduler:          │
                                │   - crawl (24h)          │
                                │   - geocode (1h)          │
                                │   - image enrich (6h)      │
                                └───────────────────┘
```

### 2.2 Backend
- **Framework:** FastAPI (Python 3.12), async throughout
- **DB access:** SQLAlchemy 2.0 (async) + asyncpg driver
- **Hosting:** Railway, Docker-based multi-stage build
- **Services split:**
  - `church-finder` — HTTP-facing web service, healthcheck at `/health`, no scheduler
  - `alert-truth` — background worker only, no HTTP surface, runs the scrape/geocode/
    enrich schedule
- **Rate limiting:** slowapi, 60 requests/min per IP on search-heavy routes (protects
  the Groq API free tier used for enrichment/classification)
- **Migrations:** currently `Base.metadata.create_all()` on startup —
  **recommended before next schema change:** migrate to Alembic (already a dependency,
  not yet wired up)

### 2.3 Data pipeline
- **Scrapers:** per-source classes in `app/scrapers/`, each declaring `source_type`
  (`httpx` for static/API-driven sources, `playwright` for JS-rendered sources)
- **Dedup:** by primary key `id` (derived from source + listing identity) —
  re-scraped listings that already exist are skipped, not duplicated
- **Schedule:** crawl every 24h, geocode hourly, image enrichment every 6h
  (tuned down from an initial 3h interval — see §7 rationale)
- **~30 configured sources**, roughly 12–15 currently yielding real data; several
  blocked by bot protection (403/405) or awaiting Playwright conversion — tracked as
  an ongoing backlog, not a launch blocker

### 2.4 Frontend
- **Stack:** React 18 + TypeScript + Vite
- **State/data:** TanStack Query (server state), Zustand (client state)
- **Routing:** React Router
- **HTTP:** Axios, base URL via `VITE_API_URL` env var (already parameterized —
  no hardcoded localhost)
- **Hosting:** Vercel, custom domain `ulouka.com`

### 2.5 Environments
| Concern | Value |
|---|---|
| Backend prod URL | `https://church-finder-production-43ab.up.railway.app` |
| Frontend prod URL | `https://ulouka.com` (Vercel) |
| DB | Railway-managed Postgres |
| Scheduler timezone | `Europe/London` (explicit, not server-default) |

### 2.6 Known technical debt (tracked, not urgent)
1. Schema managed by `create_all()`, not Alembic migrations
2. No indexes confirmed on frequently-filtered columns (location, price, source) —
   worth adding before traffic scales
3. Several scrapers blocked by bot protection; Playwright conversion path defined
   but only one source (`Church in Wales`) actioned so far
4. No analytics/event tracking yet (§9)
5. No automated tests visible in the pipeline discussed so far

---

## 3. MVP Scope

### 3.1 Must-have (launch blockers)
- [x] Backend live, stable, healthchecked
- [x] Scraper pipeline running on a sane daily cadence
- [x] Deduplication working correctly
- [ ] Frontend live at `ulouka.com` with working search/listing views
- [ ] CORS correctly configured for the live domain
- [ ] Basic listing detail page (title, price, location, images, source link,
      property type)
- [ ] Basic search/filter (location, price range, property type)
- [ ] Mobile-responsive layout

### 3.2 Should-have (fast-follow, not launch blockers)
- Dynamic homepage stats (live listing count, regions, active sources — see the
  stats endpoint we scoped earlier)
- Favourites (router already scaffolded — `favourites.router`)
- Basic SEO (router already scaffolded — `seo.router`)
- Email enquiry forwarding (router already scaffolded — `enquiry.router`)

### 3.3 Explicitly deferred past MVP
- User accounts / saved searches with alerts
- Playwright-based scraping for bot-protected sources beyond Church in Wales
- Analytics/event tracking system
- Any monetization mechanism
- Sacred Spaces cross-linking/unification (kept as a separate related property for now)

---

## 4. User Flow

### 4.1 Primary flow — discover a property
```
Land on ulouka.com
   │
   ▼
See homepage: live stats + featured/recent listings
   │
   ▼
Search or filter (location / price / property type)
   │
   ▼
Browse results grid
   │
   ▼
Open a listing detail page
   │
   ▼
View images, description, price, location, source
   │
   ▼
Click through to original source listing (external link)
   │
   ▼
[Deferred] Save to favourites / sign up for alerts
```

### 4.2 Secondary flow — location-first browsing
```
Land on ulouka.com
   │
   ▼
Browse by region/map view
   │
   ▼
See listings clustered by area
   │
   ▼
Same detail → source-link flow as above
```

### 4.3 Return-visit flow (post-MVP, once alerts exist)
```
Receive email: "3 new listings matching your saved search"
   │
   ▼
Click through directly to filtered results
```

---

## 5. Design System

**[ASSUMPTION — confirm]** No visual design language has been defined in our
conversations yet. Below is a starting proposal grounded in the subject matter
(ecclesiastical architecture, calm/trustworthy property-search tone) — treat as a
first draft to react to, not a final decision.

### 5.1 Tone
Calm, trustworthy, slightly architectural — closer to a well-run property portal
than a religious or ornate aesthetic. The buildings are the visual interest; the UI
should stay quiet.

### 5.2 Suggested palette
| Role | Direction |
|---|---|
| Primary | Deep stone/slate blue — evokes stained glass without being literal |
| Accent | Warm stone/sandstone neutral — echoes church masonry |
| Background | Off-white / warm grey, not pure white |
| Text | Near-black, high contrast for readability |
| Success/Active | Muted green (for "active listing" states) |

### 5.3 Typography
- **Headings:** a serif with some character (evokes heritage buildings) —
  e.g. Fraunces, Source Serif, or similar
- **Body/UI:** a clean, highly legible sans — e.g. Inter, IBM Plex Sans
- Avoid anything overtly "churchy" (script fonts, gothic blackletter) — undermines
  the professional property-portal feel

### 5.4 Components (map to existing routers)
- Listing card (grid item): image, title, price, location badge, property-type tag
- Listing detail page: image gallery, price, location, description, source-link CTA
- Filter bar: location, price range, property type, sort
- Stats strip (homepage): live listings / regions / active sources — **dynamic**,
  per the stats endpoint discussed
- Empty states: "No listings match your filters" with a suggestion to broaden search

### 5.5 Spacing/grid
Standard 8px baseline grid, responsive breakpoints at mobile / tablet / desktop —
no unusual layout needed given this is a straightforward search-and-browse product.

---

## 6. Database Schema

### 6.1 Current — `listings` table (as deployed)
```sql
CREATE TABLE listings (
    id             VARCHAR NOT NULL PRIMARY KEY,
    source         VARCHAR NOT NULL,
    title          VARCHAR NOT NULL,
    price          VARCHAR,
    location       VARCHAR,
    url            VARCHAR,
    description    TEXT,
    images         TEXT,              -- JSON-encoded array
    lat            FLOAT,
    lon            FLOAT,
    geocoded       BOOLEAN,
    is_off_market  BOOLEAN,
    notified       BOOLEAN,
    first_seen     TIMESTAMP WITHOUT TIME ZONE,
    last_seen      TIMESTAMP WITHOUT TIME ZONE,
    is_active      BOOLEAN
);
```

### 6.2 Recommended additions before scaling traffic
```sql
-- Indexes for the filter/search columns actually queried by app/routers/search.py
CREATE INDEX idx_listings_location   ON listings (location);
CREATE INDEX idx_listings_source     ON listings (source);
CREATE INDEX idx_listings_is_active  ON listings (is_active);
CREATE INDEX idx_listings_last_seen  ON listings (last_seen DESC);
```

### 6.3 Proposed — `site_stats` (supports dynamic homepage stats, computed once
per crawl rather than queried live)
```sql
CREATE TABLE site_stats (
    id                SERIAL PRIMARY KEY,
    live_listings     INTEGER NOT NULL,
    regions_covered   INTEGER NOT NULL,
    active_sources    INTEGER NOT NULL,
    computed_at       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);
```

### 6.4 Proposed — `favourites` (matches existing `favourites.router` scaffold)
**[ASSUMPTION — confirm]** exact shape depends on whether favourites are
account-bound or anonymous/session-bound at MVP.
```sql
CREATE TABLE favourites (
    id            SERIAL PRIMARY KEY,
    user_id       VARCHAR,           -- nullable if anonymous/session-based at MVP
    session_id    VARCHAR,           -- fallback for pre-account favouriting
    listing_id    VARCHAR NOT NULL REFERENCES listings(id),
    created_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);
```

### 6.5 Proposed — analytics tables (post-MVP, see §9)
```sql
CREATE TABLE page_views (
    id            SERIAL PRIMARY KEY,
    path          VARCHAR NOT NULL,
    referrer      VARCHAR,
    session_id    VARCHAR,
    created_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE search_events (
    id            SERIAL PRIMARY KEY,
    query_params  JSONB,             -- filters used: location, price range, type
    result_count  INTEGER,
    session_id    VARCHAR,
    created_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE listing_clicks (
    id            SERIAL PRIMARY KEY,
    listing_id    VARCHAR NOT NULL REFERENCES listings(id),
    session_id    VARCHAR,
    created_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);
```

---

## 7. Monetization Plan

**Not needed for launch** — deliberately deferred until there's real traffic and
usage data to make informed decisions. Documented here as a forward-looking menu,
not a commitment.

### 7.1 Options, roughly ordered by fit for this niche
1. **Featured/promoted listings** — property agents or auction houses pay for
   priority placement. Requires an agent-facing submission flow (not built yet).
2. **Lead referral fees** — commission from partner agents/auction houses for
   enquiries routed through the site. Requires partnership agreements.
3. **Affiliate links** — architects, conversion specialists, surveyors, planning
   consultants relevant to church conversions. Lower effort, lower ceiling.
4. **Premium alerts** — free basic search, paid tier for instant/filtered email
   alerts on new matching listings. Natural fit once user accounts exist.
5. **Data licensing** — aggregated, anonymised market data (volume of listings,
   regional trends, price ranges) licensed to researchers, journalists, or
   conservation bodies. Plausible given the Sacred Spaces / dataset angle.

### 7.2 Recommended sequencing
Don't monetize until: (a) consistent weekly traffic exists, (b) you know which
pages/features people actually use. Premium alerts (#4) is the most natural first
step since it requires infrastructure you'll likely build anyway (user accounts,
saved searches).

---

## 8. Launch Plan

### 8.1 Pre-launch checklist
- [ ] Frontend live at `ulouka.com` with SSL
- [ ] CORS configured for the live domain
- [ ] All MVP-scope routes functional end-to-end (search → detail → source link)
- [ ] Mobile check on at least one real phone, not just devtools
- [ ] `/health` and both Railway services stable for 48h+ before announcing
- [ ] Basic `robots.txt` + sitemap (ties into the existing `seo.router`)
- [ ] Privacy note / disclaimer that listings link to third-party sources (you
      don't control their accuracy/availability)

### 8.2 Launch sequence (soft → public)
1. **Soft launch (private):** share with a handful of trusted contacts
   (e.g. Living Christ Mission UK network, given your existing charity involvement)
   for real-world testing before any public push
2. **Fix anything broken** surfaced by that small group
3. **Public soft launch:** post in relevant niche communities (see §9) without
   heavy promotion — let organic interest build
4. **Monitor:** Railway metrics (memory/CPU), error logs, and whatever basic
   analytics exist at that point

### 8.3 What "launched" means here
No big-bang requirement — this is a low-stakes, zero-cost launch. "Live and
correct" is the bar, not "viral," given the deliberately narrow niche.

---

## 9. User Acquisition Plan

Given the niche (church/chapel conversions, UK-specific), acquisition is about
**precision over volume** — a small, highly relevant audience matters more than
broad reach.

### 9.1 Free channels, roughly ordered by fit
1. **Niche online communities** — architecture/conversion forums, r/AskUK,
   r/HousingUK, r/architecture, property developer forums, Facebook groups for
   barn/church/chapel conversions
2. **SEO** — this is a genuinely underserved search niche ("former church for
   sale UK," "chapel conversion for sale," etc.) — the `seo.router` scaffold
   suggests this was already anticipated; prioritise clean metadata, sitemap,
   and fast page loads
3. **Existing Sacred Spaces / Living Christ Mission network** — you already have
   a relevant audience and credibility in adjacent spaces; a natural first
   distribution channel, no cold outreach needed
4. **Journalists/bloggers covering church closures** — this is a recurring UK
   news topic (declining congregations, heritage building reuse); a well-timed
   outreach email with your aggregated data could earn organic coverage
5. **Property/architecture Twitter (X) and LinkedIn** — developers and architects
   interested in adaptive reuse are active there; low-cost, high-relevance

### 9.2 What to avoid at this stage
- Paid ads — not worth the spend pre-monetization and pre-validation
- Broad/generic property listing communities — wrong audience, low relevance

---

## 10. Growth Plan

### 10.1 Phase 1 — Validate (0–3 months post-launch)
- Confirm people actually return and search repeatedly (not just one-time visits)
- Fix scraper coverage gaps identified in production (§2.6)
- Ship dynamic stats, favourites, basic SEO — the "should-have" MVP items

### 10.2 Phase 2 — Retain (3–6 months)
- User accounts + saved search alerts (the natural next big feature — also
  unlocks premium monetization later)
- Expand Playwright-covered sources for previously-blocked listings
  (Rightmove, Zoopla, Church of Scotland, etc.) — via the separate containerized
  Playwright pathway already scoped
- Basic analytics (page_views / search_events tables from §6.5) to see what's
  actually being searched for and clicked

### 10.3 Phase 3 — Expand (6–12 months)
- Consider Sacred Spaces integration/cross-linking now that both products have
  independent traction (rather than merging prematurely)
- Evaluate first monetization mechanism based on real usage data (§7)
- Consider geographic or category expansion (e.g. other heritage building types
  beyond churches, if demand signals point that way) — **not** a given, only if
  data supports it

### 10.4 Guardrails throughout
- Don't add infrastructure complexity (Kubernetes, paid scraping proxies, etc.)
  until a specific, evidenced need justifies it — consistent with the approach
  already taken on hosting decisions
- Don't monetize before retention is proven
- Keep the scraping pipeline within reasonable, respectful request patterns —
  this is a long-term project, not a land-grab

---

## Appendix — Open questions to resolve

1. Primary target persona for MVP messaging (developers vs. faith communities vs.
   general public)?
2. Favourites: account-bound or anonymous/session-based at first?
3. Final relationship between `ulouka.com` and `sacredspaces.church` — fully
   separate brands, or linked/cross-promoted from launch?
4. Any existing brand assets (logo, colour preferences) for §5, or starting from
   the proposal above?
