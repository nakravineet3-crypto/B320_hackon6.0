# MissionCart Deep-Dive Teaching Prompt

Paste everything below this line into a new Claude conversation.

---

You are a senior software architect and engineering mentor. I built a product called **MissionCart** for Amazon HackOn 2026 and I want you to teach me everything about it in depth — the system design, the algorithms, the data flows, the tradeoffs, the alternatives, and the production implications. Teach me like I'm a smart engineer who built it but hasn't fully understood *why* every decision was made.

Here is the complete technical context of the system:

---

## What MissionCart Is

MissionCart is an **Occasion Operating System** built on top of Amazon Now (10-20 minute delivery). The core insight: Amazon Now solved the delivery problem. The unsolved problem is the **decision** problem — users spend 8–15 minutes figuring out what to order for any goal-driven occasion (birthday party, house setup, trek, potluck). MissionCart eliminates that decision work entirely.

**One-line pitch:** "Amazon Now delivers in minutes. MissionCart makes sure you ordered the right things."

**Team:** Anmol Jain + Vineet Nakra. Built over ~1 week for a hackathon finals.

---

## Tech Stack

### Backend
- **Language:** Python 3.11
- **Framework:** FastAPI (async) + Uvicorn
- **LLM:** Groq `llama-3.1-8b-instant` (primary), Anthropic Claude Sonnet (fallback), Amazon Bedrock (target for production)
- **Embeddings:** BLaIR `hyp1231/blair-roberta-large` — fine-tuned RoBERTa-large on Amazon product data, dim=1024
- **Vector Search:** FAISS `IndexFlatIP` (cosine similarity on L2-normalized vectors) — 15,000 products
- **Deployment:** Railway + Docker
- **Data:** JSON files (catalog.json 15K products, simulated purchase history 50 users)
- **Data Source:** McAuley Lab Amazon 2023 dataset (6 categories, ~4.7 GB compressed)

### Frontend
- **Framework:** React Native 0.74 / Expo SDK 51
- **Navigation:** Expo Router (file-based routing)
- **State:** Zustand
- **Animations:** Reanimated 3
- **Styles:** StyleSheet.create() only (no inline styles)
- **Types:** TypeScript, 0 errors enforced

### Key Algorithms
- EWMA (Exponential Weighted Moving Average) for depletion prediction
- LIFT scoring for identity-group product affinity
- Cosine cold-start for new user cluster assignment
- Temporal relevance scoring (piecewise function) for occasion feed
- 6-stage cart building pipeline
- 7-phase deterministic comparison engine
- 5-gate demo detection for audit engine

---

## Feature 1: Smart Reorder (Morning Approval)

**What it does:** Predicts which household products U001 will run out of in the next few days and presents a one-tap morning approval card. No manual list-building.

**Algorithm — EWMA with adaptive alpha:**
- Formula: `EWMA_n = α × interval_n + (1-α) × EWMA_{n-1}`
- Alpha adapts to purchase consistency:
  - Consistent buyers (CV < 0.15): α = 0.20 (stable baseline, trust recent data more)
  - Erratic buyers: α = 0.50 (higher mean reversion)
- Confidence score: `score = consistency × data_volume × recency`
- `data_volume = 1 - exp(-n/6.0)` — smooth asymptote, never a step function
- Items with confidence < 0.35 are silently filtered

**Anomaly detection:** Three regimes detected and excluded from EWMA updates:
- Bulk/sale purchases: price < 80% of median → likely stocking up, not normal interval
- Gap anomaly: interval > 2.5× EWMA → out of stock or forgot
- Regime change: interval > 3.5× EWMA → behavioral shift

**Bundle scoring:** `urgency(0.45) + confidence(0.30) + value(0.15) + now_eligible(0.10)`

**Fallback chain (3 levels — server never fails to start):**
1. `depletion_predictions.json` — pre-materialized, hot path, < 1ms
2. `user_product_features.json` — rebuild predictions in < 500ms
3. `depletion_alerts.json` — static fallback, days_remaining computed at request time

**Key files:**
- `backend/app/services/ewma_engine.py` — pure math, no I/O
- `backend/app/services/depletion_engine.py` — central service + singleton
- `backend/app/routers/reorder.py` — API endpoint
- `backend/app/data/simulated/depletion_predictions.json` — pre-materialized

---

## Feature 2: Goal Cart Build (6-Stage Pipeline)

**What it does:** User types "Birthday party for 12 kids tomorrow under ₹4000" → complete, validated, ready-to-order cart in < 3 seconds.

**The LLM design principle (critical):** LLM parses intent and explains results. It NEVER selects products, sets quantities, or decides the final cart. All decisions are deterministic algorithms. This makes the system auditable, testable, and reliable.

**6-stage pipeline:**

**Stage 1 — Goal Parsing (LLM + regex fallback)**
- Input: raw natural language goal + budget
- LLM extracts: occasion_type, headcount, deadline, safety_requirements, budget
- Output: MissionSpec (Pydantic model)
- Fallback: regex extracts numbers and keywords if LLM unavailable
- Groq llama-3.1-8b with 2-level prompt cache (memory TTL + disk persistent)

**Stage 2 — Profile Engine (Taxonomy + LLM-generated)**
- Layer 1: `occasion_need_taxonomy.json` — 11 human-curated need lists for known occasions (instant, no LLM)
- Layer 2: LLM generates need list for unknown occasions on first request, cached permanently
- Community enrichment: `community_need_signals.json` adjusts need priorities from 4,401 purchase sessions
- Per-user EWMA: α_removal=0.30, α_keep=0.08, α_added=0.20 (asymmetric — deliberate removal weighted more)
- Feature flag: `USE_PROFILE_ENGINE=false` by default

**Stage 3 — Quantity Planning**
- Formula-based: `quantity = ceil(headcount × usage_rate × buffer ÷ pack_size)`
- Examples: plates = headcount × 2, balloons = headcount × 5, cups = headcount × 1.5
- Rules stored in `quantity_rules.json`, overridable per occasion type

**Stage 4 — Constraint Filtering (8 checks)**
1. Budget: `item_cost ≤ remaining_budget × 1.1`
2. Delivery ETA: must arrive before deadline
3. Amazon Now: if deadline ≤ 24h, must be Now-eligible
4. Safety tags: child_safe/baby_safe/pet_safe required when flagged
5. Return risk: < 30% threshold (high return = quality signal)
6. Quality floor: rating ≥ 3.5
7. Social completeness: group-size items present
8. Sponsored gate: blocked if fails any above check

**Stage 5 — Budget Repair (5-step sequence)**
1. Trim quantity buffers (round down)
2. Swap to cheaper substitute in same category
3. Drop optional items by ascending price
4. Drop should_have items
5. NEVER drop must_have items (coverage always maintained)

**Stage 6 — Coverage Score + Explanation**
- Coverage = categories_filled / must_have_needs
- LLM Haiku writes explanation copy for each item (templated in demo mode)
- Response includes: items, coverage_pct, budget_used, flags, community_signal

**Key files:**
- `backend/app/services/cart_builder.py` — 6-stage orchestrator
- `backend/app/services/mission_parser.py` — LLM + regex
- `backend/app/services/profile_engine.py` — adaptive profiles
- `backend/app/services/quantity_planner.py` — formulas
- `backend/app/services/constraint_engine.py` — 8 checks
- `backend/app/services/budget_repair.py` — repair logic

---

## Feature 3: Cart Audit

**What it does:** Takes any Amazon cart and runs it through 8 rules. The demo cart has exactly 4 flags that animate in sequence with a "Fix All" CTA.

**Two code paths (critical for demo reliability):**
- **Demo path:** `is_demo_cart()` — 5-gate detection (birthday keyword → 3-6 items → plates+balloon+cups → sponsored+non-Now → sponsored item has empty safety_tags) → returns hardcoded 4 flags deterministically. Demo CANNOT fail.
- **Real path:** Runs full constraint engine against actual cart items

**4 demo flags (in order):**
1. Quantity insufficiency — "12 plates for 12 kids, need 24" (RED)
2. Missing accessory — "Balloon set has no pump" (AMBER) — from compatibility graph
3. Delivery failure — "Streamers not Amazon Now eligible" (AMBER)
4. Sponsored trust violation — "Cups are sponsored and failed child_safe" (BLUE/info)

**Real path checks (8 types):** quantity, missing dependency, delivery eligibility, sponsored, child safety, return risk (> 30%), quality floor (rating < 3.5), social completeness

**Repair logic:**
- `increase_quantity` — actually updates repaired_cart items
- `swap_product` — queries catalog for best alternative
- `add_product` — adds missing accessory
- `budget_repair` — drops optional items by price ascending

**Flag sorting:** red(0) > blue(1) > amber(2), missing_accessory first, social_completeness last

**Coverage scoring:** `coverage = len(filled_needs) / len(must_have_needs)` — real computation from `occasion_need_taxonomy.json`, not mock percentage

**Key files:**
- `backend/app/services/audit_engine.py` — demo + real paths
- `frontend/src/app/audit.tsx` — SACRED, never modified

---

## Feature 4: AI Comparison Engine

**What it does:** Detects when a user switches between two products 3+ times (hesitation behavior) and auto-surfaces a goal-aware comparison. "For your birthday mission, Set A wins because the balloon count exactly matches your headcount."

**Switching detection (frontend, O(1)):**
- Tracks `lastViewedAsin` + `switchCount` in local React state
- Trigger: same category, 2 unique ASINs, 3+ switches within 60s sliding window
- Calls `/api/comparison/evaluate` on trigger

**7-phase comparison engine:**
1. Extract mission context from active cart goal
2. Retrieve full product details for both ASINs
3. Score both: price (lower wins), rating, Amazon Now eligibility, child_safe tag, return_risk, mission fit
4. Apply community evidence multiplier [0.95–1.05]
5. Identify winner by total score
6. Generate LLM explanation anchored to mission context (Groq)
7. Return structured result with winner declared, score breakdown, audit trace

**LLM principle:** Numerical scoring is deterministic. LLM only writes the explanation sentence, never changes the winner.

---

## Feature 5: Identity Groups (Novel Primary Claim)

**What it does:** Groups users by behavioral identity (not demographics) and shows what "people like you actually buy" with zero sponsored products.

**The pitch:** "Amazon connects products to products. We connect people to people."

**4 identity groups:** Office Gym Dad, JEE Student, College Girl, Home Chef

**LIFT scoring algorithm:**
```
lift(product, cluster) = cluster_adoption_rate / global_adoption_rate
cluster_adoption_rate = buyers_in_cluster / cluster_size
global_adoption_rate = buyers_globally / total_users
```
- Suppresses universal items (everyone buys milk → lift ≈ 1.0)
- Surfaces identity-distinctive products (only JEE students buy this → lift = 3.85×)
- Threshold: lift ≥ 1.2, minimum 2 group buyers

**K-Means clustering:**
- Feature vectors: per-user category spending proportions (normalized)
- Sharp centroid separation: office_gym_dad fitness=1.00, jee_student stationery=1.00, college_girl beauty=1.00, home_chef grocery=1.00+kitchen=1.00

**Cold-start for new users:**
- Cosine similarity to cluster centroids: `sim(user_vec, centroid_k) = dot(u,c) / (|u||c|)`
- Assign to nearest centroid in O(K) time
- No training required for new user

**Data:**
- `purchase_history.json` — 4,659 orders, 50 users, real Amazon ASINs
- `cluster_product_affinities.json` — top-20 LIFT products per group
- `community_groups.json` — 4 group definitions with centroids

**Frontend:**
- Horizontal pill selector, trust badge ("Zero sponsored products"), 2-column FlatList grid
- Real `<Image>` when `image_url` available, color placeholder fallback
- Spring animations on pill tap

**Key files:**
- `backend/app/services/community_engine.py` — LIFT computation + cluster serving
- `backend/app/routers/community.py` — dynamic catalog lookup by category+rating
- `frontend/src/app/(tabs)/discover.tsx` — pills + grid

---

## Feature 6: Occasion Intelligence Feed

**What it does:** Shows upcoming Indian occasions (Diwali, birthdays, potlucks, treks) with urgency states, estimated budgets, and countdown timers. Each card launches a pre-filled goal cart.

**Relevance formula:**
```
relevance = 0.45×temporal + 0.25×history_default + 0.20×identity + 0.10×community_default
```

**Temporal relevance — piecewise function:**
```
days_until > 60 (discovery):    0.3 × (1 - days/180)
14 ≤ days ≤ 60 (preparation):  0.6 + 0.2 × (60-days)/46
1 ≤ days ≤ 13 (urgent):        0.8 + 0.15 × (13-days)/12
days = 0 (emergency):           1.0
```

**Urgency states (4 levels):**
- discovery (60+ days): indigo #5C6BC0
- preparation (14-59 days): orange #FF6B00
- urgent (1-13 days): red #E53935
- emergency (day-of): dark red #B71C1C

**Occasion calendar:** 10 real 2026-2027 dates with `tap_goal` (full pre-filled goal string — NOT bare "Diwali"), `headcount_default`, `estimated_budget_inr`, `community_signal`, `discovery_days_before`, `prep_days_before`

**Keyword-based occasion detection in parser:**
```python
OCCASION_KEYWORDS = {
    "diwali": "diwali_celebration",
    "birthday": "kids_birthday",
    "potluck": "office_potluck",
    ...
}
```
Falls back to LLM only when no keyword match. Parser no longer hardcodes kids_birthday for all goals.

**Key files:**
- `backend/app/services/occasion_engine.py` — deterministic feed, no LLM
- `backend/app/data/occasion_calendar.json` — 10 occasions with real dates
- `frontend/src/app/(tabs)/discover.tsx` — full-width urgency cards

---

## Feature 7: Semantic Search

**What it does:** Product search with two layers — exact substring match (instant) falling back to BLaIR + FAISS for typos, synonyms, and related terms.

**BLaIR model:** `hyp1231/blair-roberta-large`
- RoBERTa-large fine-tuned specifically on Amazon product-review pairs
- dim=1024, trained to encode both queries and products in the same semantic space
- Key advantage over generic BERT: understands "protein powder" ≈ "whey" ≈ "gym supplement"

**FAISS IndexFlatIP:**
- Flat index (no compression, no approximation) — exact nearest neighbor
- Inner product on L2-normalized vectors = cosine similarity
- 15,000 vectors at dim=1024 = 58.6 MB index
- Query time: < 3ms for top-10 neighbors

**Search pipeline:**
1. Substring match against title + category (< 1ms) — if ≥ 3 results, return immediately
2. BLaIR encodes query → 1024-dim vector → FAISS returns top-10 nearest neighbors
3. Badge engine annotates: `amazon_now`, `organic` (not sponsored), `high_rated`, `best_value`
4. Suggestions for empty states trigger goal cart build

**Known P1 issue:** FAISS post-filter by category partially negates semantic benefit — if semantic result is in wrong category bucket, it gets filtered out before serving

**FAISS rebuild pipeline:**
- `scripts/rebuild_faiss_index.py` encodes 15K products at ~5 products/s on CPU (~53 min)
- Batch size 32, device: cpu (no GPU on Railway)
- Also writes `catalog_embedded.json` for retrieval engine

---

## Feature 8: Quorum (Group Cart)

**What it does:** Collaborative cart for groups — flatmates, event committees. Members vote on items, split budget, and chat.

**Optimizer (3 rules):**
1. Remove items with net negative votes
2. Swap single units to family packs when group_size > 3
3. Deduplicate ASINs (keep highest-voted)

**Payment split modes:** Equal | Proportional (by items claimed) | Custom

---

## Feature 9: Community Goal Pages

**What it does:** Shared shopping coordination — multiple people claim items ("I'll bring the balloons") to eliminate duplicate purchases.

**3 seeded pages:** Sharma Family Diwali (5 people, 63% claimed, 118 days), Office Potluck (8 people, 43% claimed, 3 days), Arjun's Birthday (3 people, 78% claimed, 7 days)

**API:** `GET /goals`, `GET /goals/{id}`, `POST /goals` — all under `/api/community/`
**days_until** computed dynamically server-side from target_date vs today
**Coverage** recomputed on every GET from claimed item count

---

## Real Amazon Catalog Integration

### Dataset
McAuley Lab Amazon 2023 dataset — 6 categories:
- Health_and_Personal_Care (22 MB compressed)
- Grocery_and_Gourmet_Food (309 MB)
- Pet_Supplies (381 MB)
- Home_and_Kitchen (2.8 GB) — the bottleneck
- Toys_and_Games (628 MB)
- Office_Products (504 MB)

Each product record: asin, title, description, images (CDN URLs), price, rating, review_count, categories hierarchy, bought_together (for compatibility graph), features list

### Build Pipeline
1. **Download** — `scripts/download_amazon_data.py` (patched with HTTP Range resume — no restart from zero on crash), aria2c for 8-connection parallel download
2. **ETL** — `scripts/build_amazon_catalog.py`:
   - `MAX_PER_FILE = 4,000` cap (prevents memory exhaustion on 2.8GB Home_and_Kitchen)
   - Normalizes categories to internal taxonomy (toys_games, stationery, personal_care, etc.)
   - Preserves demo product ASINs (B001PLATES etc.) from previous catalog via merge
   - Writes `catalog.json` (15K products, 9.5 MB) + `compatibility_graph.json`
3. **FAISS** — `scripts/rebuild_faiss_index.py` — ~53 min on CPU

### Catalog Stats (15,000 products)
toys_games: 2,331 | stationery: 2,126 | personal_care: 2,000 | pet_care: 1,769 | household: 1,253 | beverages: 819 | storage: 810 | snacks: 489 | food_beverages: 454 | decorations: 413

### Image URLs
Amazon CDN format: `https://m.media-amazon.com/images/I/[hash]._AC_SL1500_.jpg`
The raw dataset includes full image arrays per product. Extraction scans all 6 gz files to match the 15K catalog ASINs. No auth required to fetch — public CDN.

---

## Data Architecture

### Simulated Data
All simulation disclosed to judges with `simulated_data: true` on every API response.

| File | Content | Real/Simulated |
|------|---------|----------------|
| `catalog.json` | 15,000 real Amazon products | **REAL** (McAuley Lab) |
| `purchase_history.json` | 4,659 orders, 50 users | Simulated with real ASINs |
| `community_groups.json` | 4 K-Means cluster definitions | Simulated |
| `cluster_product_affinities.json` | LIFT scores per group | Computed from simulation |
| `occasion_calendar.json` | 10 occasions with real 2026 dates | Hand-curated |
| `depletion_predictions.json` | EWMA predictions per user | Computed from simulation |
| `community_goal_pages.json` | 3 sample goal pages | Seeded demo data |

### User Model (U001 = Sneha, the demo user)
- Group: college_girl (for discovery)
- Depletion alerts: household items (Ariel, Head & Shoulders, Pedigree)
- Birthday party cart (for audit demo)
- Purchase history spans 18 months

---

## API Design

### Response Envelope (consistent across all endpoints)
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "request_id": "uuid4",
  "simulated_data": true
}
```

### Key Endpoints
```
POST /api/mission/build        — 6-stage cart building pipeline
POST /api/mission/audit        — cart audit (demo or real path)
GET  /api/reorder/draft        — EWMA depletion predictions
GET  /api/occasions/feed       — temporal relevance feed
GET  /api/community/groups/:id/products — LIFT-ranked identity products
GET  /api/community/goals      — goal page summaries
POST /api/comparison/evaluate  — 7-phase comparison
GET  /api/search/products      — FAISS semantic search
GET  /health                   — always 200, never fails
```

---

## LLM Architecture

### Provider Hierarchy
1. Groq `llama-3.1-8b-instant` — primary (free, ~200ms, no streaming)
2. Anthropic Claude Sonnet — fallback
3. Amazon Bedrock Claude — target for production
4. Regex parser — emergency fallback (0ms, always works)

### Prompt Caching (2 levels)
- Memory TTL cache: identical prompts within session → instant
- Disk persistent cache: across restarts → same goal second time is instant

### LLM Factory Pattern
```python
# factory.py
def get_provider() -> LLMProvider:
    if GROQ_API_KEY: return GroqProvider()
    if ANTHROPIC_API_KEY: return AnthropicProvider()
    return RegexFallbackProvider()
```

### The Non-LLM Design Principle
LLM is ONLY used for:
1. Parsing natural language goal → MissionSpec (structured extraction)
2. Writing explanation copy for cart items ("why this product")
3. Writing comparison justification text

LLM is NEVER used for:
- Selecting products (FAISS + catalog query)
- Setting quantities (formula library)
- Budget decisions (constraint engine)
- Audit flag generation (rule engine)
- Occasion ranking (temporal formula)

**Why:** Deterministic systems are testable, auditable, and reliable. LLM hallucinations in product selection = wrong items in cart = broken demo.

---

## Frontend Architecture

### Screen Structure
```
(tabs)/
  index.tsx        — Home: morning approval card, occasion cards
  discover.tsx     — Identity groups + occasions + community goals
community/
  goal.tsx         — Goal page detail (participants, items, claim)
  trekking.tsx     — Static screen
cart/
  building.tsx     — Animated building state
  result.tsx       — Cart result with coverage score
audit.tsx          — SACRED — 4-flag animation sequence (never touched)
search.tsx         — FAISS search + switching detection
reorder/           — Draft, confirmation, placing screens
hive/              — Quorum group cart screens
```

### State Management
- **Zustand** for global state (persona, cart, session)
- **Local useState** for screen-specific state (switching detection, animations)
- **No Redux** — overkill for this app size

### Animation System
- **Reanimated 3** for all animations
- Audit flags: staggered entrance, 1.5s between each flag
- Cart building: progress bar + spinning indicator
- Identity group grid: opacity fade-in (250ms) on selection
- Comparison sheet: slide up from bottom

### Sacred Rules (Non-negotiable)
1. `audit.tsx` — NEVER TOUCH (the judge-facing moment, pixel-perfect)
2. `simulated_data: true` on every API response (transparency)
3. `StyleSheet.create()` only — no inline styles
4. TypeScript 0 errors always
5. LLM explains, never decides
6. Health endpoint always returns 200
7. Feature name: QUORUM (not Hive, not CartPool)

---

## Infrastructure & Deployment

### Hackathon Stack
- **Backend:** Railway + Docker, Python 3.11, single worker
- **Frontend:** Expo Go on Android device, LAN IP connection to backend
- **LLM:** Groq free tier (~200ms, rate limited)
- **Data:** JSON files in Docker image (no external DB)

### Production AWS Mapping
| Hackathon | AWS Production |
|-----------|---------------|
| Railway + Docker | ECS Fargate + ALB |
| JSON catalog | DynamoDB (products) + S3 (media) |
| FAISS local index | Amazon OpenSearch (vector search) |
| `compatibility_graph.json` | Amazon Neptune (graph DB) |
| Groq LLM | Amazon Bedrock (Claude Sonnet reserved) |
| Hardcoded occasions | Amazon EventBridge (Indian calendar trigger) |
| K-Means clusters | Amazon Personalize (real-time serving) |
| Morning push | Amazon SNS + FCM |
| JSON files | Aurora PostgreSQL (user data, orders) |

### Scale Numbers
- 3M Amazon Now orders/day → 20% occasion-driven = 600K MissionCart sessions/day
- 10 min saved per session = 100K customer-hours/day recovered
- Infrastructure cost < 0.001% of GMV (₹48 crore/day at avg ₹800 cart)

---

## Known Tradeoffs and Alternatives

### FAISS IndexFlatIP vs HNSW
- **Chose:** IndexFlatIP (exact, no approximation)
- **Why:** 15K vectors at dim=1024 is small enough for exact search in < 3ms
- **Alternative:** HNSW (faster for millions of vectors, approximate, graph-based)
- **Production:** Amazon OpenSearch with k-NN plugin (managed HNSW)

### BLaIR vs sentence-transformers
- **Chose:** BLaIR (blair-roberta-large, Amazon-specific fine-tuning)
- **Why:** Fine-tuned on Amazon review/product pairs — understands retail semantics better than generic models
- **Alternative:** `all-MiniLM-L6-v2` (smaller, faster, generic), `text-embedding-3-small` (OpenAI, API cost)
- **Tradeoff:** BLaIR is 1.3 GB download, slow CPU inference (5 products/s), but much better retail relevance

### JSON Files vs Database
- **Chose:** JSON files
- **Why:** Zero infrastructure overhead for hackathon, version controlled, readable
- **Alternative:** SQLite (still file-based but queryable), PostgreSQL (production-grade)
- **Tradeoff:** No concurrent writes (fine for hackathon), full file load on startup (fine for 15K products)

### Groq vs Anthropic vs Bedrock
- **Chose:** Groq as primary
- **Why:** Free tier, fast (~200ms), no credit card for hackathon
- **Alternative:** Anthropic Claude (better quality, costs money), Bedrock (production target, AWS-native)
- **Tradeoff:** Groq rate limits can hit during demo; 3-level fallback chain mitigates this

### K-Means vs Collaborative Filtering
- **Chose:** K-Means on purchase vectors
- **Why:** Interpretable clusters, fast cold-start via cosine similarity, no training infrastructure
- **Alternative:** Matrix Factorization (SVD, ALS), Graph Neural Networks, Amazon Personalize
- **Tradeoff:** K-Means doesn't capture item-item relationships, can't do next-item prediction. Fine for identity grouping, wrong for "you might also like"

### Deterministic Pipeline vs End-to-End LLM
- **Chose:** Deterministic pipeline with LLM at edges (parsing + explanation)
- **Why:** Reliable, testable, auditable. LLM cart selection = unpredictable items, wrong quantities, hallucinated products
- **Alternative:** Single LLM call with tool use / function calling to query catalog
- **Tradeoff:** More code, but every bug is findable and fixable. LLM bugs are unpredictable.

### Expo Go vs Native Build
- **Chose:** Expo Go
- **Why:** Faster iteration, no native build toolchain needed, runs on any Android device instantly
- **Alternative:** EAS Build (native .apk), bare React Native
- **Tradeoff:** Expo Go has module restrictions (no custom native modules), but sufficient for all features built

### EWMA vs ML Regression for Depletion
- **Chose:** EWMA
- **Why:** Explainable ("your average reorder interval is 18 days"), no model training, works on small N (5-10 orders), adaptive alpha handles behavioral changes
- **Alternative:** Linear regression, ARIMA, Prophet (overkill for 5 data points per product)
- **Tradeoff:** EWMA misses seasonality (buy more Dettol in monsoon). Production: Amazon Forecast with seasonal indices.

---

## What to Teach Me

Please go deep on each of the following areas. For each one, explain:
1. **What it is** and why this project uses it
2. **How it works** mechanically (math, pseudocode, or step-by-step)
3. **Why this choice** over the alternatives
4. **What breaks** when it fails and how the fallbacks work
5. **How it would differ in production** at Amazon scale

**Areas:**

1. **EWMA depletion prediction** — the math, adaptive alpha, anomaly detection, confidence scoring, and why this beats a simple "reorder every N days" approach

2. **LIFT scoring for identity groups** — the formula, why it suppresses universal items, how it's different from simple co-occurrence, and what collaborative filtering would have done differently

3. **BLaIR + FAISS semantic search** — how embedding models work, why cosine similarity on normalized vectors equals inner product, what FAISS IndexFlatIP does differently from HNSW, and what the post-filter problem actually is

4. **The 6-stage cart building pipeline** — walk me through each stage, the data that flows between stages, what Pydantic models look like, and how the LLM principle (explains, never decides) is enforced architecturally

5. **The audit engine's 5-gate demo detection** — why this exists, what makes it brittle, and how it would be eliminated in production

6. **Temporal relevance scoring for occasions** — the piecewise function, what "relevance" means in this context, and how the 4 weighted components interact

7. **The LLM fallback chain** — how multi-provider LLM routing works, what prompt caching achieves, and why the regex fallback exists

8. **K-Means clustering for identity groups** — feature vector construction, centroid interpretation, and why cosine cold-start is better than random assignment for new users

9. **FastAPI lifespan warmup** — what cache warming achieves for demo reliability, why the 3 goals were chosen, and what happens if warmup fails

10. **The deterministic vs probabilistic design philosophy** — why the entire system is designed so the LLM can never break the demo, and what the failure modes of an end-to-end LLM approach would have been

Take your time. I want to genuinely understand why each decision was made, not just what was built.
