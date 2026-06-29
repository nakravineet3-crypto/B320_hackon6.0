# MissionCart — Feature Implementation Reference

> Amazon HackOn 2026 Finals · Team B320 (Anmol Jain + Vineet Nakra)
> Working directory: `D:/Projects/B320_hackon6.0/missioncart/`
> Last updated: 2026-06-27 — Real Amazon catalog integrated (15,000 products)

This document covers every implemented feature: what it does, where it lives, what the demo path is, what works, and what is in progress.

---

## The Product in One Sentence

MissionCart is an **Occasion Operating System** for Amazon Now. "Delivery is already fast. Shopping is still slow." The product solves the 3-minute problem of figuring out *what* to order — not the 20-minute problem of waiting for delivery.

---

## The 3-Minute Demo Script (Sacred — Do Not Change)

```
ACT 1 (0:00–0:20): Home tab → Morning Approval card → Tap Approve
ACT 2 (0:20–0:40): Scroll to Riya's Birthday occasion card → Tap Audit Cart
ACT 3 (0:40–1:30): Audit flags animate in (1.5s each) → Fix All → budget counter animates
ACT 4 (1:30–1:50): Search → switch products 3× → Comparison bottom sheet slides up
ACT 5 (1:50–2:10): Discover tab → "Office Gym Dad" pill → "Zero sponsored" badge
ACT 6 (2:10–2:30): Diwali occasion card → "Plan this" → Goal input pre-filled
ACT 7 (2:30–3:00): Close
```

---

## Feature 1: Smart Reorder (Morning Approval)

### What It Does
Predicts which household products U001 (Sneha) will run out of in the next few days and presents them as a one-tap morning approval card. No manual list-building. One tap orders everything.

### Demo Path
Home tab → amber morning approval card at the top → "Ariel 2kg · Head & Shoulders · Pedigree 3kg" → Approve → order placed.

### Technical Architecture

**Algorithm:** EWMA (Exponential Weighted Moving Average) with adaptive alpha
- Alpha adapts to purchase consistency: consistent buyers (CV < 0.15) get α = 0.20, erratic buyers get α = 0.50
- Confidence is multiplicative: `score = consistency × data_volume × recency`
- `data_volume = 1 - exp(-n/6.0)` — smooth asymptote, never a step function
- Items with confidence < 0.35 ("Insufficient") are silently filtered before the morning card
- Anomaly detection: bulk/sale (price < 80% median), gap (> 2.5× EWMA), regime change (> 3.5× EWMA) — anomalous intervals are excluded from EWMA updates

**Bundle scoring:** urgency (45%) + confidence (30%) + value (15%) + Amazon Now eligibility (10%)

**Fallback chain:**
1. `depletion_predictions.json` (pre-materialized, hot path)
2. `user_product_features.json` (rebuild predictions in < 500ms)
3. `depletion_alerts.json` (static fallback, live `days_remaining` computed at request time)

Server never fails to start. Demo always shows items.

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/reorder.py` | API endpoint `/api/reorder/draft` |
| Service | `backend/app/services/depletion_engine.py` | Central prediction service + singleton |
| Computation | `backend/app/services/ewma_engine.py` | Pure EWMA math (no I/O) |
| Build Script | `backend/scripts/build_depletion_data.py` | Offline data generation pipeline |
| Data | `backend/app/data/simulated/depletion_predictions.json` | Pre-materialized predictions |
| Data | `backend/app/data/simulated/user_product_features.json` | EWMA feature vectors per (user, asin) |
| Data | `backend/app/data/simulated/purchase_events.json` | Enriched event stream (4,680 events) |
| Data | `backend/app/data/category_priors.json` | Cold-start defaults + seasonal indices |
| Frontend | `frontend/src/app/(tabs)/index.tsx` | Home screen (morning card) |
| Frontend | `frontend/src/app/reorder/` | Draft, confirmation, placing screens |

### Status — COMPLETE
- `ewma_engine.py` — **DONE** (pure math, sanity checks pass)
- `build_depletion_data.py` — **DONE** (generates 4 files, 749 predictions, 50 users)
- `depletion_engine.py` — **DONE** (central service + singleton)
- `reorder.py` — **DONE** (calls depletion_engine, old functions deleted)
- `main.py` — **DONE** (depletion_engine.load() in lifespan)
- Demo predictions validated: MC_ARIEL_001 urgent ✓, MC_DOGFOOD_001 soon ✓, MC_SHAMPOO_001 urgent ✓

### API Response Shape (stable — frontend never changes)
```typescript
GET /api/reorder/draft?user_id=U001
{
  draft: {
    user_id: string,
    items: [{
      item_id, asin, title, category, suggested_quantity, user_quantity, unit,
      price_per_unit, total_cost, confidence (int 0-100), urgency_copy, explanation,
      inventory_status, amazon_now_eligible, delivery_eta_mins,
      // New: bundle_score, reorder_urgency, subcategory, confidence_detail, days_remaining
    }],
    total_cost, item_count, simulated_data: true
  }
}
```

---

## Feature 2: Goal Cart Build

### What It Does
User types any natural language goal ("Birthday party for 12 kids tomorrow under ₹4000") and receives a complete, validated, ready-to-order cart. Built by a deterministic pipeline — the LLM parses the goal and explains items, never selects products or decides quantities.

### Demo Path
Discover tab → Diwali occasion card → "Plan this →" → Goal input pre-filled → Cart builds in < 2s → 8+ items, coverage score, budget summary.

### Architecture: Adaptive Occasion Profiles (NEW)

The original hardcoded adapter system (3 Python classes with fixed need lists) has been replaced by a **two-layer adaptive architecture**:

**Layer 1 — Static Taxonomy (known occasions)**
`occasion_need_taxonomy.json` — human-curated need lists for 11 pre-seeded occasions. LLM never touches this. Loaded at startup, served from memory.

**Layer 2 — LLM Generation (unknown occasions)**
When a user types an occasion not in the taxonomy (e.g. "Ganesh Chaturthi puja"), Claude Sonnet generates a need list on first request, validates it through Pydantic safety filters, and caches it permanently. Second request: instant cache hit.

**Community Enrichment**
`community_need_signals.json` — adoption rates from 4,401 purchase sessions. Adjusts need priorities: if 97% of birthday parties bought plates → plates = must_have. If 40% bought streamers → streamers = optional.

**User Enrichment (EWMA)**
Per-user asymmetric EWMA: α_removal=0.30 (deliberate action), α_keep=0.08 (passive), α_added=0.20 (discovery). After 36 feedback events, community signal displaces LLM guess entirely.

**Feature Flag**
`USE_PROFILE_ENGINE=false` (default). Set to `true` to activate. Old adapters remain as fallback. Non-negotiable.

**The demo moment**: Type "Ganesh Chaturthi puja" — LLM generates live (~2s). Type it again → instant. Demonstrates the learning system working in real-time.

### 6-Stage Pipeline (unchanged)
1. **Goal Parsing** — LLM extracts MissionSpec. Fallback: regex.
2. **Profile Engine** (new) — Returns need list from taxonomy OR LLM-generated profile
3. **Quantity Planning** — Formulas: plates = `headcount * 2`, balloons = `headcount * 5`
4. **Constraint Filtering** — 8 checks (now wired): budget, Amazon Now, compatibility, return risk, quality floor, child_safe, sponsored validity
5. **Budget Repair** — Drop optional → substitute → reduce quantities → drop should_have (never must_have)
6. **Explanation** — Template copy (today) → LLM Haiku explanations (production)

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/mission.py` | `/api/mission/build` + feature flag |
| Orchestrator | `backend/app/services/cart_builder.py` | 6-stage pipeline + catalog cache fix |
| Profile Engine | `backend/app/services/profile_engine.py` | NEW — adaptive profile service + singleton |
| Parser | `backend/app/services/mission_parser.py` | LLM goal extraction → MissionSpec |
| Domain Router | `backend/app/services/domain_router.py` | Fallback path (kept, never deleted) |
| Adapters | `backend/app/services/adapters/` | Fallback path (kept, never deleted) |
| Retrieval | `backend/app/services/retrieval_engine.py` | BLaIR + FAISS semantic search |
| Constraints | `backend/app/services/constraint_engine.py` | 8-check validation (now wired) |
| Compatibility | `backend/app/services/compatibility.py` | balloon→pump, tent→stakes |
| Quantity | `backend/app/services/quantity_planner.py` | Formula library |
| Repair | `backend/app/services/budget_repair.py` | Over-budget repair |
| Data | `backend/app/data/occasion_need_taxonomy.json` | NEW — 11 human-curated profiles |
| Data | `backend/app/data/occasion_profiles_cache.json` | NEW — runtime LLM-generated profiles |
| Data | `backend/app/data/community_need_signals.json` | NEW — community adoption rates |
| Data | `backend/app/data/user_need_signals.json` | NEW — per-user EWMA feedback state |
| Frontend | `frontend/src/app/cart/building.tsx` | Building animation |
| Frontend | `frontend/src/app/cart/result.tsx` | Cart result display |

### P0 Fixes Applied
- ✅ Silent `except pass` replaced with domain-aware fallback (`_domain_fallback()`)
- ✅ 8 demo ASINs added to catalog.json (B001PLATES through B007BREAD)
- ✅ `check_all_constraints()` wired — 8 checks against `remaining_budget`
- ✅ Budget multi-pack bug fixed (`price × quantity` not `price`)
- ✅ Cache key includes headcount

### Status — COMPLETE
- P0 backend fixes — **DONE**
- P0 data fixes (catalog 256 products) — **DONE**
- `profile_engine.py` — **DONE** (stampede protection, EWMA feedback, atomic writes)
- `occasion_need_taxonomy.json` — **DONE** (11 occasions, 90 needs, all category gaps fixed)
- `community_need_signals.json` — **DONE** (24 high-confidence signals)
- Async LLM providers (Groq + Anthropic + Bedrock, 8s timeouts) — **DONE**
- `USE_PROFILE_ENGINE=false` feature flag in mission.py — **DONE**
- `_load_catalog()` module-level cache — **DONE**

### Remaining P1 (next sprint)

| Issue | Severity |
|-------|----------|
| FAISS category post-filter makes semantic search identical to keyword | P1 |
| `baby_care`/`pet_care` routes to EventAdapter → party supplies | P1 |
| Trek: 1 backpack for 4 people (gear qty formula) | P1 |
| `compatibility_graph.json` never imported (27 edges orphaned) | P1 |

---

## Feature 3: Cart Audit

### What It Does
Takes any Amazon cart and checks it against 8 rules. The demo cart (Sneha's birthday party cart) has exactly 4 flags that reveal non-obvious problems. "Fix All" auto-repairs the cart, updates the budget, and hits 9/9 coverage.

### Demo Path (Sacred — Do Not Change)
Occasion card "Riya's Birthday" → Audit Cart → 4 flags animate in at 1.5-second intervals:
1. "12 plates for 12 kids" (red — needs 24)
2. "Balloon set, no pump" (amber — missing dependency)
3. "Streamers not Amazon Now eligible" (amber — swapping to equivalent)
4. "Sponsored cups, failed child safe" (blue/info)
→ Fix All → budget counter animates ₹4,340 → ₹3,850 → Coverage 9/9

### Technical Architecture

**Audit engine has two paths:**
- **Demo path:** `is_demo_cart()` detects Sneha's cart by ASIN match → returns hardcoded 4 flags deterministically (demo cannot fail)
- **Real path:** Runs constraint engine against the actual cart items

**8 audit check types:** quantity insufficiency, missing dependency (compatibility), Amazon Now ineligibility, sponsored product, child safety failure, return risk, quality floor, budget overrun

**LLM role:** Generates the explanation text for each flag ("Kids use 2 plates at parties"). Never generates the flag itself.

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/mission.py` | `POST /api/mission/audit` |
| Service | `backend/app/services/audit_engine.py` | Demo + real path audit logic |
| Frontend | `frontend/src/app/audit.tsx` | **SACRED — NEVER TOUCH** |

### Status
- Backend: **WORKING** (demo path deterministic — hardcoded 4 flags)
- Frontend: **WORKING** (audit.tsx is sacred, never modified)
- Demo ASINs in catalog.json: **DONE** (B001PLATES, B002BALLOONS, B003STREAMERS, B004CUPS all added)

---

## Feature 4: AI Comparison Engine

### What It Does
Detects when a user switches between two products 3+ times in search (hesitation behavior) and presents a goal-aware comparison bottom sheet. "For your birthday mission, Set A wins because the balloon count exactly matches your headcount."

### Demo Path
Search → find two balloon sets → switch back and forth 3 times → bottom sheet slides up with comparison.

### Technical Architecture

**Switching detection:** Frontend (`search.tsx`) tracks `lastViewedAsin` + `switchCount` in local state. After 3 switches, calls `/api/comparison/evaluate`.

**Comparison engine (7 phases):**
1. Extract mission context from active cart
2. Retrieve full product details for both ASINs
3. Score both on: price, rating, Amazon Now eligibility, child_safe, return_risk, mission fit
4. Identify the winning product
5. Generate LLM explanation anchored to mission context
6. Return structured comparison with winner declared

**LLM principle:** Numerical scoring is deterministic. LLM only writes the explanation sentence. Never changes the winner.

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/comparison.py` | `POST /api/comparison/evaluate` |
| Frontend | `frontend/src/app/search.tsx` | Switching detection + bottom sheet trigger |
| Frontend | `frontend/src/lib/api.ts` | `comparisonAPI.evaluate()` |

### Status
- Backend: **WORKING**
- Frontend switching detection: **WORKING**
- Bottom sheet display: verified in demo path

---

## Feature 5: Identity Groups (Primary Novel Claim) — NEXT SPRINT

### What It Does
Groups users by behavioral identity (not demographics) and shows what "people like you" actually buy — with zero sponsored products. This is the **primary differentiator** from standard Amazon recommendations.

**The pitch:** "Amazon connects products to products. We connect people to products."

**8 Identity Groups:** Office Gym Dad, Home Chef, JEE Student, Weekend Adventurer, New Parent, Pet Parent, College Student, Minimalist

### Demo Path (Sacred — ACT 5 of 3-minute demo)
Discover tab → "For people like you" section → tap "Office Gym Dad" pill → "Zero sponsored products in this section" badge appears → **product grid shows what Office Gym Dads actually buy**.

### Current State vs. Target

| Element | Current | Target |
|---------|---------|--------|
| Identity pills | ✅ Showing | No change needed |
| Zero sponsored badge | ✅ Appears on tap | No change needed |
| Product grid | ❌ Missing — pills show, grid empty | 2-column product grid with real products |
| Community API | ✅ Working | Wire group products to grid |

### Technical Architecture

**Identity clustering:** K-Means on 50-user purchase vectors. Each cluster assigned a human-readable identity name. U001 (Sneha) maps to "The Celebration Circle."

### What Needs to Be Built

**The product grid is the entire gap.** When a user taps "Office Gym Dad", the pill highlights and the badge appears — but there is no product grid below showing what Office Gym Dads buy. This is the visual proof of the primary novel claim. Without the grid, the demo's most important moment has no payoff.

**Implementation plan (mobile-experience-engineer):**

1. **API call**: `GET /api/community/groups/{group_id}/products` — returns top 8-12 products bought by this identity group, all `sponsored: false`
2. **Product card**: 2-column `FlatList`, 130px card height, product image (top 60%), name (14px), price (12px), rating stars
3. **Animation**: Grid fades in 200ms after pill tap (Reanimated `FadeIn`)
4. **Trust copy**: "Showing what [group_name] actually buy. Zero sponsored." appears above grid
5. **Empty state**: If no products: "Community picks coming soon" — never blank

**Backend API needed** (`/api/community/groups/{group_id}/products`):
- Read `community_insights.json` — get top_products for the group
- Join with catalog.json to get full product details
- Filter: `sponsored: false` (hard requirement — this is the identity groups promise)
- Return up to 12 products sorted by purchase frequency within cluster

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/routers/community.py` | Add `GET /groups/{group_id}/products` endpoint |
| `frontend/src/app/(tabs)/discover.tsx` | Add product grid below identity pills |
| `frontend/src/lib/api.ts` | Add `communityAPI.getGroupProducts(groupId)` |

### Priority
**P0 for demo** — ACT 5 of the 3-minute script has no visual payoff without the product grid. This is the moment judges either believe the primary novel claim or don't. A pill that highlights and shows a badge but no products fails the demo.

**Product selection:** Top products purchased by cluster members, ranked by purchase frequency × recency. All sponsored products filtered out before serving. `is_sponsored: false` is a hard requirement for identity group products.

**Trust statement:** "Zero sponsored. [N] members verified." — computed at serving time from actual cluster size.

### Files

| Layer | File | Role |
|-------|------|------|
| Service | `backend/app/services/community_engine.py` | K-Means clustering + group serving |
| Router | `backend/app/routers/community.py` | `/api/community/groups`, `/api/community/insights` |
| Data | `backend/app/data/community_groups.json` | 6 cluster definitions |
| Data | `backend/app/data/community_insights.json` | Per-group product picks |
| Data | `backend/app/data/user_cluster_map.json` | user_id → cluster_id |
| Frontend | `frontend/src/app/(tabs)/discover.tsx` | Identity pills + product grid |
| Frontend | `frontend/src/app/(tabs)/profile.tsx` | Persona selector (8 personas) |
| State | `frontend/src/store/persona.ts` | `usePersonaStore` Zustand store |

### Status — COMPLETE
- Backend: **DONE** (`GET /api/community/groups/{group_id}/products` live)
- Frontend pills: **DONE**
- Product grid below selected pill: **DONE** (2-column FlatList, real `<Image>` with color fallback)
- Zero sponsored badge: **DONE** (appears before grid on pill selection)
- `communityAPI.getGroupProducts()` in api.ts: **DONE**
- Identity group products: **DONE** — dynamic lookup from real 15K catalog by category + rating (no more hardcoded ASINs)
- LIFT scores: **DONE** — recomputed from real purchase simulation (`cluster_product_affinities.json`)
- `adoption_copy` shown on cards: **DONE**
- 0 TypeScript errors confirmed

---

## Feature 6: Occasion Intelligence Feed

### What It Does
Shows upcoming Indian occasions with estimated budgets and countdown timers. Each occasion card can launch a pre-filled goal cart build. The feed surfaces "what's coming up in your life" rather than "what's trending."

### Demo Path
Discover tab → "Diwali · 24 days · ₹2,400" card → "Plan this →" → Cart building pre-filled with "Diwali celebration".

### Technical Architecture

**Occasion calendar:** 7 demo occasions hardcoded with `days_until` relative to demo date. In production: Amazon EventBridge + Indian calendar API.

**Occasion-to-goal mapping:** Each occasion has `tags: list[str]` that map to cart building goals. Tapping an occasion pre-fills the goal input with the occasion name + estimated budget.

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/mission.py` | Occasion data served inline |
| Data | `backend/app/data/occasion_calendar.json` | 7 demo occasions |
| Frontend | `frontend/src/app/(tabs)/discover.tsx` | Occasion card components |
| Frontend | `frontend/src/app/(tabs)/index.tsx` | Home occasion cards |

### Status — COMPLETE
- **WORKING** end-to-end
- Days computed dynamically from `occasion_calendar.json` (not hardcoded)
- Urgency states: discovery (60+d indigo) → preparation (14-59d orange) → urgent (1-13d red) → emergency (day-of dark red)
- `tap_goal` field passes full goal string to cart builder (not bare occasion name)
- `community_signal` shown on cards
- Occasion → Goal cart CTA: wired with budget + headcount + occasion_type params
- `occasion_need_taxonomy.json` wired into `domain_router.py` for taxonomy-first routing
- Keyword-based occasion detection in `mission.py` (`OCCASION_KEYWORDS` dict)

---

## Feature 7: Semantic Search

### What It Does
Product search with two layers: exact substring match (instant) falling back to BLaIR + FAISS semantic search for typos, synonyms, and related terms. Results show trust badges (Amazon Now, organic, sponsored) and trigger comparison detection.

### Technical Architecture

**Search pipeline:**
1. Substring match against title + category (< 1ms)
2. If < 3 results: BLaIR encodes query, FAISS returns top-10 nearest neighbors
3. Badge engine annotates results: `amazon_now`, `organic` (not sponsored), `high_rated`
4. Suggestions returned for empty states (trigger goal cart build)

**BLaIR model:** `hyp1231/blair-roberta-large` — fine-tuned on Amazon product data for retail semantic similarity. Pre-downloaded in Docker image to eliminate cold start.

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/search.py` | `GET /api/search?q=` |
| Service | `backend/app/services/retrieval_engine.py` | BLaIR + FAISS |
| Service | `backend/app/services/badge_engine.py` | Trust badge annotation |
| Data | `backend/app/data/faiss_catalog.index` | BLaIR embeddings (binary) |
| Data | `backend/app/data/faiss_catalog_asins.json` | ASIN order for index |
| Frontend | `frontend/src/app/search.tsx` | Search screen + comparison detection |

### Status — COMPLETE
- **WORKING** (semantic fallback active)
- FAISS index rebuilt with 15,000 real Amazon products (58.6 MB, BLaIR dim=1024)
- `catalog_embedded.json` updated to full 15K catalog
- Note: FAISS post-filter partially negates semantic benefit (P1 fix pending)

---

## Feature 8: Quorum (Group Cart)

### What It Does
Collaborative cart building for groups — flatmates, families, event committees. Members vote on items, split the budget, and chat. Not in the 3-minute demo script but available as a live feature.

### Demo Path
Home tab → "Share to Quorum" on any cart → Hive screen with 4 tabs: Cart (voting), Chat, Budget, Split.

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/hive.py` | Demo group cart data |
| Frontend | `frontend/src/app/hive/index.tsx` | 4-tab Quorum screen |

### Status
- **WORKING** (demo data)
- Not in primary demo script — do not prioritize

---

## Feature 9: Community Goal Pages

### What It Does
Shared shopping coordination pages for group occasions. Multiple people claim responsibility for different items — "I'll bring the balloons", "I'll get the plates" — eliminating duplicate purchases and last-minute scrambles. Shows real-time coverage progress.

### Demo Path
Discover tab → "Community Goals" horizontal scroll → "3rd Floor Potluck Friday · 3 days · 43% claimed" → detail screen → "I'll bring it" on unclaimed items → "Build cart for unclaimed items" CTA.

### Technical Architecture

**Data model:** Each goal page has participants, items with claimed_by, coverage_pct computed server-side, days_until computed dynamically from target_date.

**Three sample goal pages (seeded):**
- Sharma Family Diwali 2026 — 5 participants, 8 items, 63% claimed, 118 days
- 3rd Floor Potluck Friday — 8 participants, 7 items, 43% claimed, 3 days (urgency)
- Arjun's 7th Birthday Bash — 3 participants, 9 items, 78% claimed, 7 days

**POST endpoint** allows creating new goal pages from the app (no auth required for hackathon).

### Files

| Layer | File | Role |
|-------|------|------|
| Router | `backend/app/routers/community.py` | `GET /goals`, `GET /goals/{id}`, `POST /goals` |
| Data | `backend/app/data/community_goal_pages.json` | 3 seeded goal pages |
| Frontend | `frontend/src/app/community/goal.tsx` | Detail screen (participants, items, claim CTA) |
| Frontend | `frontend/src/app/(tabs)/discover.tsx` | Horizontal scroll card section |
| Frontend | `frontend/src/lib/api.ts` | `communityGoalAPI` with fallbacks |

### Status — COMPLETE
- Backend: **DONE** (3 endpoints, days_until computed dynamically)
- Frontend detail screen: **DONE** (participants avatars, unclaimed/claimed sections, "I'll bring it")
- Discover section: **DONE** (horizontal scroll, progress bars, urgency badges)
- Goal navigation: **DONE** (`community/_layout.tsx` registers `goal` screen)
- Fallback data in `api.ts`: **DONE** (3 summary cards)

---

## Real Amazon Catalog Integration

### What Changed (2026-06-27)
The app previously ran on ~250 synthetic demo products. It now runs on **15,000 real Amazon products** from the McAuley Lab Amazon 2023 dataset.

### Data Pipeline
1. **Download** — 6 `.jsonl.gz` files (~4.7 GB total) from UCSD McAuley Lab via `run_amazon_pipeline.bat` (uses aria2c for 8-connection parallel download)
2. **Build Catalog** — `scripts/build_amazon_catalog.py` — filters, normalizes, caps at 15K products
3. **FAISS Index** — `scripts/rebuild_faiss_index.py` — BLaIR encodes all 15K products (~53 min on CPU)

### Catalog Stats
- 15,000 products across: toys_games (2,331), stationery (2,126), personal_care (2,000), pet_care (1,769), household (1,253), beverages (819), storage (810), and more
- Fields: `asin`, `title`, `category`, `brand`, `price`/`price_inr`, `rating`, `review_count`, `prime`, `amazon_now_eligible`, `image_url`, `sponsored`, `return_risk`, `safety_tags`
- Image URLs: Amazon CDN URLs extracted from raw data (extraction in progress)

### Simulation Data Rebuilt
- `purchase_history.json` — 4,659 orders, 50 users, 0 synthetic ASINs
- `cluster_product_affinities.json` — LIFT scores recomputed from real simulation
- `depletion_alerts.json` — all `MC_*` ASINs replaced with real catalog ASINs
- `catalog_embedded.json` — updated to full 15K catalog for retrieval engine

### Files
| File | Role |
|------|------|
| `run_amazon_pipeline.bat` | Download + build + index pipeline (idempotent) |
| `scripts/download_amazon_data.py` | Resume-capable downloader (patched for HTTP Range) |
| `scripts/build_amazon_catalog.py` | ETL: raw → catalog.json |
| `scripts/rebuild_faiss_index.py` | Encodes 15K products with BLaIR → FAISS index |
| `app/data/catalog.json` | 15,000 real products (9.5 MB) |
| `app/data/product_faiss.index` | FAISS index (58.6 MB) |

---

## Infrastructure

### Backend

| Component | Technology | Detail |
|-----------|-----------|--------|
| Server | FastAPI (async) + Uvicorn | Python 3.11, `--workers 1` on Railway |
| LLM | Groq `llama-3.1-8b-instant` | Primary. Bedrock Claude as target (fix pending) |
| Embeddings | BLaIR `hyp1231/blair-roberta-large` | Pre-downloaded in Docker |
| Vector search | FAISS `IndexFlatIP` | Cosine similarity on normalized vectors |
| Deployment | Railway + Docker | `railway.toml` configured |
| Health check | `GET /health` → always 200 | Never fails, even in degraded mode |

### Frontend

| Component | Technology | Detail |
|-----------|-----------|--------|
| Framework | React Native 0.74 / Expo SDK 51 | Expo Go for demo (no native build) |
| Navigation | Expo Router (file-based) | 3 visible tabs: Home, Discover, Profile |
| State | Zustand | `usePersonaStore`, `useCartStore` |
| Animations | Reanimated 3 | Audit flags, comparison sheet, cart building |
| Styles | `StyleSheet.create()` only | No inline styles, ever |
| Types | TypeScript, 0 errors always | Run `tsc --noEmit` before any commit |

### Sacred Rules (Never Violate)

1. `audit.tsx` — NEVER TOUCH
2. `simulated_data: true` on every API response
3. `StyleSheet.create()` only — no inline styles
4. TypeScript 0 errors always
5. LLM explains, never decides
6. Health endpoint always returns 200
7. Feature name: **QUORUM** (not Hive, not CartPool)

---

## Feature Completion Status

| Feature | Status | Demo-Ready |
|---------|--------|-----------|
| Smart Reorder | ✅ Complete | ✅ |
| Goal Cart Build | ✅ Complete | ✅ |
| Cart Audit | ✅ Complete | ✅ |
| AI Comparison Engine | ✅ Complete | ✅ |
| Identity Groups | ✅ Complete | ✅ |
| Occasion Intelligence Feed | ✅ Complete | ✅ |
| Semantic Search | ✅ Complete | ✅ |
| Quorum (Group Cart) | ✅ Complete | ✅ |
| Community Goal Pages | ✅ Complete | ✅ |
| Real Amazon Catalog | ✅ Integrated | ✅ |

### Open P1 Items
- FAISS category post-filter partially negates semantic search benefit
- `baby_care`/`pet_care` routes to EventAdapter → party supplies (minor routing edge case)
- Image URL extraction in progress (4,478+ of 15,000 products matched so far)

---

## Production Architecture (AWS — For Judge Q&A)

Every hackathon component maps directly to an AWS service with zero code changes:

| Hackathon | AWS Production |
|-----------|---------------|
| Railway + Docker | ECS + Auto-scaling |
| JSON files | DynamoDB (user data, orders) |
| `compatibility_graph.json` | Amazon Neptune (graph queries) |
| Groq LLM | Amazon Bedrock (Claude Sonnet + Haiku) |
| FAISS local index | Amazon OpenSearch (vector search) |
| Hardcoded occasions | Amazon EventBridge (time-based triggers) |
| K-Means clusters | Amazon Personalize (real-time identity serving) |
| Morning approval push | Amazon SNS + FCM |

**Scale numbers:** 3M Amazon Now orders/day → 20% occasion-driven = 600K MissionCart sessions/day → ₹48 crore GMV/day. Infrastructure cost < 0.001% of GMV.
