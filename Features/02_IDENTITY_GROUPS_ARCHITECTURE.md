# Feature 2: Identity Groups & Behavioral Persona System
## Full Architecture Design — Amazon Scale

---

## 1. Problem Statement

Amazon currently connects **products to products** ("customers who bought X also bought Y").
MissionCart connects **people to people** ("shoppers with your basket pattern buy this 3.2× more than average").

The challenge: how do you automatically understand who a user is from what they buy —
without asking them, without inferring sensitive identity, and at a scale of 200M+ users?

---

## 2. The Three-Layer Mental Model

Every decision in this system must respect these three distinct layers.
Mixing them up is the single most common failure in persona systems.

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1 — PRODUCT TAXONOMY                                  │
│ What the item IS.                                           │
│ Fixed, business-owned. Never discovered by clustering.      │
│ Example: Dairy & Eggs, Baby Care, Snacks, Festival          │
└─────────────────────────────────────────────────────────────┘
         ↓ products are tagged with taxonomy
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2 — BEHAVIORAL COHORT                                 │
│ What shopping PATTERN the user belongs to.                  │
│ Discovered by math. Never manually defined.                 │
│ Example: "Baby Essentials Replenisher",                     │
│          "Weekly Staples Planner", "Fitness Snack Buyer"    │
└─────────────────────────────────────────────────────────────┘
         ↓ cohorts are named by LLM + safety filter
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3 — DISPLAY LABEL                                     │
│ How we safely explain the cohort to the user in the UI.     │
│ Behavior-based, never identity-based.                       │
│ Example: "Baby Care Replenishment Pattern"                  │
│ NEVER: "New Parent", "Mom", "Dad", "JEE Student"            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Product Taxonomy (Layer 1) — Fixed 20 Categories

These are fixed. Clustering does NOT create or modify these.

```
 1. Dairy & Eggs
 2. Fruits & Vegetables
 3. Staples (Atta, Rice, Dal, Oil)
 4. Snacks & Namkeen
 5. Beverages & Tea & Coffee
 6. Breakfast & Spreads
 7. Instant Food & Noodles
 8. Bakery & Biscuits
 9. Chocolates & Sweets
10. Dry Fruits & Nuts
11. Frozen Food & Ice Cream
12. Cleaning & Household
13. Personal Care & Grooming
14. Baby Care
15. Pet Care
16. Health & OTC
17. Party & Occasions
18. Puja & Festival
19. Home & Kitchen
20. Electronics Accessories
```

---

## 4. Where This Feature Is Used in the App

The persona/cohort system is not a standalone feature.
It plugs into 4 existing surfaces:

### 4.1 Discover Tab — Identity Groups (PRIMARY surface)
The main visual showpiece. Shows the user which behavioral cohort
they belong to and what products are distinctively bought by that cohort.

```
┌─────────────────────────────────────────────┐
│  Your Shopping Patterns                     │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Baby Care Replenishment Pattern     │    │
│  │ Based on your last 23 orders        │    │
│  │                                     │    │
│  │ Shoppers with similar baskets buy:  │    │
│  │ Pampers Premium L        3.2×  →   │    │
│  │ Johnsons Baby Powder     2.8×  →   │    │
│  │ Dettol Baby Soap         2.4×  →   │    │
│  │                                     │    │
│  │ Not sponsored · Available now ⚡    │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Weekly Staples Planner              │    │
│  │ Confidence: 68%                     │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 4.2 Cart Building — Zero-Friction Assumption Engine
When user types "weekly groceries", the persona pre-fills assumptions:
- Likely budget range
- Likely pack sizes (single vs family)
- Brand preferences (premium vs budget)
- No clarification questions asked

```
WITHOUT persona:  "weekly groceries" → asks 3 questions
WITH persona:     "weekly groceries" → instant cart, 8 items
```

### 4.3 Reorder Predictions — Cadence Personalisation
Each cohort has a characteristic reorder cadence.
Baby Care cohort: diapers every 18 days, formula every 12 days.
Weekly Staples cohort: atta every 25 days, milk every 5 days.
The depletion engine uses this to surface reorder nudges.

### 4.4 Search & Ranking — Result Bias
Same search query, different cohort → different ranked results.
"peanut butter" for Fitness Snack Buyer → protein-focused variants first.
"peanut butter" for Breakfast Replenishment Buyer → family pack first.

---

## 5. Option Analysis — All Approaches Considered

### Option A: Manual Persona Picker (Current, Rejected)
User picks "Office Gym Dad" from a list.

| | |
|---|---|
| Pros | Simple, zero ML needed |
| Cons | Users never self-select accurately. Privacy risk. Fake. Judge will destroy it. |
| Verdict | ❌ Eliminated |

---

### Option B: Collaborative Filtering (Amazon's current approach)
Item-item: "people who bought X also buy Y"

| | |
|---|---|
| Pros | Battle-tested. Works at scale. Amazon Personalize does this. |
| Cons | No person-group-item relationship. Can't explain "why". Needs massive data. |
| When to use | Production recommendation engine (Layer 4 of serving) |
| Verdict | ✅ Use in production ranking, not for Identity Groups feature |

---

### Option C: Matrix Factorization (SVD / ALS)
Decomposes user-item matrix into latent factors.

| | |
|---|---|
| Pros | Scalable. Strong baseline. Easy to implement. |
| Cons | No graph structure. Weak at basket/occasion context. Black box. |
| Library | Implicit (ALS), Surprise (SVD) |
| Verdict | ✅ Good baseline to beat. Use as benchmark. |

---

### Option D: K-Means on Purchase Vectors (Simple Clustering)
TF-IDF style user vectors → K-Means.

| | |
|---|---|
| Pros | Trivially simple. Interpretable. Fast. |
| Cons | No graph structure. Treats products as independent (loses basket context). |
| When to use | MVP / sanity check |
| Verdict | ⚠️ Use only as demo fallback if GNN fails |

---

### Option E: HDBSCAN (Density-Based, No Fixed K)
Finds clusters automatically without specifying K.

| | |
|---|---|
| Pros | Auto-discovers K. Handles noise. Finds non-spherical clusters. |
| Cons | Slow on large datasets. Harder to explain. Unstable across runs. |
| At Amazon scale | Too slow for 200M users without approximate nearest neighbours |
| Verdict | ⚠️ Good for offline analysis. Not for production serving. |

---

### Option F: Two-Tower Neural Network
Separate encoder for users and items. Train to maximise dot product for
positive pairs (user bought item) and minimise for negatives.

| | |
|---|---|
| Pros | Scales well. Used by YouTube, Pinterest. Fast ANN retrieval. |
| Cons | Doesn't capture basket-level structure. Requires negative sampling strategy. |
| At Amazon scale | Industry standard for candidate retrieval |
| Verdict | ✅ Use in production candidate generation. Not for cohort discovery. |

---

### Option G: GATv2 on User-Item-Basket Graph (CHOSEN APPROACH)
Graph Attention Network v2 on hypergraph where baskets are hyperedges.

| | |
|---|---|
| Pros | Captures basket-level context. Attention weights are interpretable. Better than GCN for heterogeneous graphs. Produces rich 128-dim user embeddings. |
| Cons | Needs graph infrastructure at scale. Training is expensive. Requires careful negative sampling. |
| Why GATv2 over GCN | GATv2 fixes the static attention problem in GATv1 — attention weights depend on both source and target, not just source. Better for commerce graphs where item context matters. |
| Why over LightGCN | LightGCN is simpler and faster but loses the attention mechanism. For basket-level signals, attention matters. |
| At Amazon scale | Runs weekly offline. Embeddings cached in FAISS. Inference is ANN lookup. |
| Verdict | ✅ CHOSEN for cohort discovery |

---

### Option H: Hypergraph Neural Network (HGNN / DHCF)
Treats baskets as true hyperedges (not decomposed into pairs).

| | |
|---|---|
| Pros | Theoretically superior. Preserves basket integrity. DHCF paper shows 5-15% lift over GCN. |
| Cons | Implementation complexity. Less library support. Harder to explain to judges. |
| Verdict | ✅ Production evolution after GATv2. Mention in PPT as next step. |

---

### Option I: Session-Based GNN (SR-GNN)
Models sequential purchase patterns within sessions.

| | |
|---|---|
| Pros | Captures "what are they buying right now" signal. Good for in-session recommendations. |
| Cons | Short-term signal only. Can't build long-term persona. |
| Verdict | ✅ Use alongside GATv2 for session-level candidate generation. Not for cohort assignment. |

---

### Option J: LLM-Only Persona Assignment
Feed purchase history to LLM, ask it to assign a persona.

| | |
|---|---|
| Pros | Zero ML infrastructure. Fast to prototype. |
| Cons | Non-deterministic. Expensive per user at scale. No mathematical grounding. Hallucination risk. Privacy: sending user data to external LLM. |
| At Amazon scale | 200M users × LLM call = impossible. |
| Verdict | ❌ Use LLM only for cluster NAMING, never for cluster DISCOVERY or ASSIGNMENT |

---

## 6. Chosen Architecture: GATv2 + GMM + LIFT

### 6.1 Full System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   OFFLINE PIPELINE                      │
│                 (runs weekly on GPU)                    │
│                                                         │
│  Purchase Events + Basket History                       │
│         │                                               │
│         ▼                                               │
│  Build Graph                                            │
│  ├── User nodes (U)                                     │
│  ├── Item nodes (I)                                     │
│  ├── User→Item edges (purchased, weighted by recency)   │
│  └── Basket hyperedges → decomposed to item-item edges  │
│         │                                               │
│         ▼                                               │
│  GATv2 Training                                         │
│  ├── 3 attention layers                                 │
│  ├── 128-dim output embeddings                          │
│  └── Trained to predict next purchase (BPR loss)        │
│         │                                               │
│         ▼                                               │
│  User Embeddings Matrix [N_users × 128]                 │
│         │                                               │
│         ▼                                               │
│  Optimal K Discovery                                    │
│  ├── Silhouette score (range K=4 to K=20)               │
│  ├── Davies-Bouldin score                               │
│  ├── Cluster size balance check (min 5% of users)       │
│  └── LIFT distinctiveness check (min 5 products ≥ 1.4) │
│         │                                               │
│         ▼                                               │
│  GMM Clustering with optimal K (target: 10-12)         │
│  └── Soft memberships (user belongs to multiple         │
│      cohorts with weights summing to 1.0)               │
│         │                                               │
│         ▼                                               │
│  LIFT Scoring per Cohort                                │
│  LIFT = (cluster_adoption / global_adoption)            │
│       × log(1 + cluster_buyers)                         │
│       × availability_score                              │
│       × trust_score                                     │
│  Filter: LIFT ≥ 1.4, cluster_buyers ≥ 3,               │
│          cluster_adoption ≥ 0.08                        │
│         │                                               │
│         ▼                                               │
│  LLM Naming                                             │
│  ├── Feed top 20 LIFT products per cohort to LLM        │
│  ├── Get 5 candidate behavior labels                    │
│  └── Safety filter (banned word list)                   │
│         │                                               │
│         ▼                                               │
│  Export JSON Files                                      │
│  ├── user_cluster_map.json                              │
│  ├── cohort_definitions.json                            │
│  └── cluster_product_affinities.json                    │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼ (files read at startup)
┌─────────────────────────────────────────────────────────┐
│                   ONLINE SERVING                        │
│                (<10ms per request)                      │
│                                                         │
│  User opens app                                         │
│         │                                               │
│         ▼                                               │
│  Redis lookup: user_id → cohort assignments             │
│         │ HIT                          MISS             │
│         │                               │               │
│         ▼                               ▼               │
│  Cached cohort weights         FAISS ANN search         │
│                                (session signals         │
│                                 → nearest centroid)     │
│         │                               │               │
│         └──────────────┬────────────────┘               │
│                        ▼                                │
│         Cohort preference profile                       │
│         ├── Top categories                              │
│         ├── Price sensitivity                           │
│         ├── LIFT products                               │
│         └── Reorder cadences                            │
│                        │                                │
│                        ▼                                │
│         ┌──────────────────────────────┐                │
│         │ Surface 1: Discover Tab      │                │
│         │ Surface 2: Cart builder bias │                │
│         │ Surface 3: Reorder nudges    │                │
│         │ Surface 4: Search ranking    │                │
│         └──────────────────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

---

### 6.2 GATv2 — Why This Specific Model

**GATv1 problem:** attention weight of node j on node i depends only on i and j's
features independently. This means the same item always gets the same attention
regardless of who is asking.

**GATv2 fix:** attention is computed as:
```
e(i,j) = a^T · LeakyReLU(W · [h_i || h_j])
```
Both nodes are concatenated BEFORE the linear transform.
This means the attention an item gets depends on who the user is.
For commerce: "baby wipes" gets high attention from a user with diaper purchases,
low attention from a student. GATv1 cannot express this. GATv2 can.

**Why this matters for Identity Groups:**
The attention weights themselves become interpretable signals.
Which items does user A attend to heavily? Those define their cohort.

---

### 6.3 LIFT Formula — Full Specification

```
Basic LIFT:
  LIFT(p, c) = cluster_adoption_rate(p, c) / global_adoption_rate(p)

Where:
  cluster_adoption_rate(p, c) = users_in_cohort_c_who_bought_p / cohort_c_size
  global_adoption_rate(p)     = users_globally_who_bought_p / total_users

Confidence-Adjusted LIFT (use this):
  score(p, c) = LIFT(p, c)
              × log(1 + cluster_buyers(p, c))
              × availability_score(p)
              × trust_score(p)

Where:
  cluster_buyers = raw count of cohort members who bought p
  availability_score = 1.0 if amazon_now_eligible else 0.3
  trust_score = (rating / 5.0) × (1 - return_risk)

Thresholds:
  LIFT ≥ 1.4                    (signal threshold)
  LIFT ≥ 1.8                    (hero card threshold)
  cluster_buyers ≥ 3            (minimum support)
  cluster_adoption_rate ≥ 0.08  (minimum penetration)
  global_adoption_rate ≥ 0.01   (item must be real product)
  sponsored == false             (zero sponsored in Discover)
  stock_available == true        (must be deliverable)

Why 1.4 not 1.2:
  At 1.2, universal items like Amul Milk leak through for every cohort.
  At 1.4, only genuinely distinctive items surface.
  At 1.8, only the identity-defining products show as hero items.
```

---

### 6.4 The 12 Behavioral Cohorts — Demo Definitions

These will be discovered by math. These are our predictions of what the
algorithm will find, based on domain knowledge of Indian purchasing patterns.
If the math finds different groupings, trust the math.

```
 1. Weekly Staples Planner
    Signal: Atta + Dal + Oil + Salt repurchased every 3-4 weeks
    Reorder cadence: atta 25 days, oil 30 days, dal 20 days

 2. Breakfast Replenishment Buyer
    Signal: Milk + Bread + Eggs + Cereal weekly cycle
    Reorder cadence: milk 5 days, bread 6 days, eggs 7 days

 3. Baby Essentials Replenisher
    Signal: Diapers + Baby Wipes + Formula + Baby Soap
    Reorder cadence: diapers 18 days, formula 12 days

 4. Fitness Snack Buyer
    Signal: Protein bars + Oats + Peanut Butter + Dry Fruits + Greek Yogurt
    Reorder cadence: protein bars 10 days, oats 20 days

 5. Budget Essentials Buyer
    Signal: Lowest price tier across all categories, private labels preferred
    Price sensitivity: highest in all cohorts

 6. Party Preparation Shopper
    Signal: Plates + Cups + Balloons + Soft Drinks + Chips in single basket
    Pattern: infrequent, high basket value, occasion-triggered

 7. Festival Preparation Shopper
    Signal: Diyas + Agarbatti + Sweets + Dry Fruits + Decor spikes seasonally
    Pattern: Diwali, Holi, Navratri correlated

 8. Pet Care Replenisher
    Signal: Dog/Cat food repurchased on strict cadence
    Reorder cadence: dog food 21 days, treats 14 days

 9. Quick Dinner Buyer
    Signal: MTR Ready Meals + Maggi + Frozen + Bread after 6pm
    Pattern: weekday evenings, small basket, fast delivery priority

10. Premium Wellness Buyer
    Signal: Organic + Supplements + High-rated products + Premium brands
    Price sensitivity: lowest (willingness to pay premium)

11. School Lunch Basket Builder
    Signal: Bread + Fruits + Juice + Biscuits + small snack packs
    Pattern: weekly, structured basket, weekday mornings

12. New Home Setup Buyer
    Signal: Cleaning + Kitchen + Storage + LED bulbs in first purchase
    Pattern: one-time large basket, then transitions to another cohort
```

---

## 7. At Amazon Scale — Production Architecture

### 7.1 Scale Numbers

```
Users:          200M active users in India
Products:       300M+ SKUs
Interactions:   10B+ events per year
Graph edges:    ~50B (user-item + item-item from baskets)
Retraining:     Weekly full retrain
Serving:        <10ms P99 for cohort lookup
```

### 7.2 Infrastructure Stack

| Component | Technology | Why |
|---|---|---|
| Graph storage | Amazon Neptune + DGL (Deep Graph Library) | Native graph operations at billion-edge scale |
| GATv2 training | AWS SageMaker + PyTorch Geometric | Distributed multi-GPU training |
| Embedding storage | FAISS on EC2 (p3.8xlarge) | ANN search across 200M embeddings in <5ms |
| Cohort cache | Redis Cluster (ElastiCache) | Sub-millisecond lookup, TTL 24 hours |
| Event streaming | Apache Kafka on MSK | 10M events/sec, durability guarantee |
| Batch pipeline | AWS EMR (Spark) | Weekly graph rebuild from raw events |
| Serving API | FastAPI on ECS | Stateless, horizontally scalable |
| Feature store | AWS SageMaker Feature Store | Online/offline parity, no training-serving skew |
| Experimentation | Amazon CloudWatch + custom A/B | Variant assignment + metric tracking |

### 7.3 Training Pipeline (Weekly)

```
Sunday 2am IST — automatic trigger

Step 1 (2 hours):  Spark job on EMR
  Read week's Kafka events from S3
  Build incremental user-item edges
  Update basket hyperedge store

Step 2 (3 hours):  GATv2 training on SageMaker
  8× A100 GPUs, data-parallel training
  3 GATv2 layers, hidden dim 256, output 128
  BPR loss with hard negative mining
  Early stopping on validation recall@20

Step 3 (30 min):  Clustering
  GMM with optimal K (re-evaluated monthly)
  Soft assignment scores per user

Step 4 (1 hour):  LIFT computation
  Spark job: compute LIFT for all (product, cohort) pairs
  Filter and rank

Step 5 (30 min):  LLM naming pass
  Only runs if cluster composition changed significantly
  Claude API: feed top LIFT products, get safe labels
  Safety filter: banned word regex

Step 6 (30 min):  Cache refresh
  Push new cohort assignments to Redis
  Update FAISS index with new centroids
  Publish new cluster_product_affinities.json

Total pipeline time: ~7.5 hours
  Completes before Monday 10am IST
  Users see updated cohorts on Monday morning
```

### 7.4 Serving Path (Online, <10ms)

```
Request: GET /discover/identity-groups
User: user_123

Step 1 (1ms):   Redis lookup → cohort weights for user_123
Step 2 (2ms):   Load top LIFT products for primary cohort
                from in-memory cluster_product_affinities
Step 3 (1ms):   Inventory filter (check stock_available flag)
Step 4 (1ms):   Build response JSON
Step 5 (1ms):   Log impression for feedback

Total: ~6ms P50, ~10ms P99

Fallback (cache miss):
  FAISS ANN search on session embedding → nearest centroid
  Use centroid's cohort profile
  Total: ~15ms (acceptable)
```

---

## 8. Privacy & Safety Architecture

### 8.1 What We Infer vs What We Show

```
What the system infers internally:
  "This user's basket pattern resembles baby care replenishment"

What we show the user:
  "Baby Care Replenishment Pattern"

What we NEVER show:
  "You appear to be a new parent"
  "Users like you as a dad"
  "Based on your family type"
```

### 8.2 Banned Label Terms

Applied as a regex filter on every LLM-generated label before it ships:

```
dad|mom|mother|father|girl|boy|man|woman|
rich|poor|luxury|budget.*class|
student|parent|baby.*parent|new.*parent|
hindu|muslim|christian|sikh|
south.indian|north.indian|regional|
young|old|elderly|teen|
male|female|gender|
pregnant|illness|medical|
salary|income|wealth
```

### 8.3 User Controls

```
User can:
  - Hide a cohort card ("not relevant")
  - Reset all pattern history
  - Opt out of behavioral grouping
  - See what data drives their pattern (transparency card)

System must:
  - Never expose raw cohort_id to client
  - Log all opt-outs and respect them in LIFT computation
  - Exclude opted-out users from cohort member_count
```

---

## 9. JSON Output Specifications

### 9.1 user_cluster_map.json

```json
{
  "user_001": {
    "primary_cohort_id": "cohort_breakfast_02",
    "memberships": [
      { "cohort_id": "cohort_breakfast_02", "weight": 0.68 },
      { "cohort_id": "cohort_budget_05",    "weight": 0.21 },
      { "cohort_id": "cohort_dinner_09",    "weight": 0.11 }
    ],
    "last_updated": "2026-06-29",
    "confidence": 0.87,
    "data_points": 47
  }
}
```

### 9.2 cohort_definitions.json

```json
{
  "cohort_breakfast_02": {
    "safe_label": "Breakfast Replenishment Buyer",
    "internal_description": "Users with repeated dairy + bakery + breakfast cycle",
    "member_count": 842,
    "top_categories": ["Dairy & Eggs", "Bakery", "Breakfast & Spreads"],
    "reorder_cadences": {
      "dairy_eggs": 5,
      "bakery": 6,
      "breakfast": 14
    },
    "price_sensitivity": "medium",
    "avg_basket_size": 6,
    "avg_order_value_inr": 680,
    "confidence": 0.87,
    "silhouette_score": 0.64,
    "llm_candidates_rejected": ["Family Breakfast Buyer", "Morning Shopper"],
    "unsafe_labels_blocked": ["Working Mom", "Family"]
  }
}
```

### 9.3 cluster_product_affinities.json

```json
{
  "cohort_breakfast_02": {
    "hero_products": [
      {
        "asin": "B0INDIRY001",
        "name": "Amul Taaza Toned Milk 1L",
        "category": "Dairy & Eggs",
        "lift": 2.4,
        "adjusted_lift": 3.87,
        "cluster_adoption_rate": 0.42,
        "global_adoption_rate": 0.175,
        "cluster_buyers": 354,
        "available_now": true,
        "sponsored": false,
        "display_explanation": "Bought regularly in similar breakfast baskets"
      }
    ],
    "standard_products": []
  }
}
```

---

## 10. Demo vs Production Comparison

| Aspect | Demo (Colab + JSON) | Production (Amazon Scale) |
|---|---|---|
| User data | 500 simulated users | 200M real users |
| Graph | Simulated interactions | 50B real edges |
| Training | Colab A100, 2-3 hours | SageMaker 8×A100, 7 hours weekly |
| Cohort discovery | GMM on Colab | Distributed GMM on EMR |
| Serving | JSON file read at startup | Redis + FAISS ANN |
| Latency | ~50ms (acceptable for demo) | <10ms P99 |
| Retraining | One-time | Weekly automated pipeline |
| LIFT computation | Python script, 500 users | Spark on EMR, 200M users |
| LLM naming | Claude API, 12 calls | Claude API, runs only on cluster change |
| Privacy | Behavior labels in JSON | Full privacy pipeline + user controls |

**What you say to judges:**
> "For the demo, embeddings are precomputed from simulated purchase history
> and served from a JSON file. The production path replaces this with weekly
> GATv2 retraining on SageMaker and sub-10ms Redis serving — the algorithm
> and the data contract are identical."

---

## 11. Evaluation Metrics

### Offline (measure before shipping)
```
Silhouette score:          > 0.45 on real data (> 0.65 on simulated)
Davies-Bouldin:            < 1.2
Cluster size balance:      no cluster < 5% of users
LIFT distinctiveness:      every cohort has ≥ 5 products with LIFT ≥ 1.4
Label safety score:        0 banned terms in any display label
```

### Online (measure after shipping)
```
CTR on LIFT products:      should exceed global product CTR
Add-to-cart from Discover: baseline vs cohort-personalised
Hide rate:                 < 5% (if higher, cohort is wrong or creepy)
Opt-out rate:              < 2% (if higher, privacy concern)
Reorder prediction accuracy: next purchase within ±3 days of prediction
```

---

## 12. Build Order for MissionCart Demo

```
Phase 1 — Colab (Anmol, 1 day)
  1. Load Amazon metadata files
  2. Simulate 500 Indian users with purchase histories
  3. Build user-item graph
  4. Train GATv2 → 128-dim embeddings
  5. Run silhouette + Davies-Bouldin → pick K
  6. GMM clustering
  7. Compute confidence-adjusted LIFT
  8. LLM naming with safety filter
  9. Export three JSON files

Phase 2 — Backend (Anmol, 2 hours after Phase 1)
  1. Replace hardcoded 4 groups with 12 discovered cohorts
  2. Wire user_cluster_map.json into auto-assignment API
  3. Wire cohort_definitions.json into cart builder assumption engine
  4. Wire cluster_product_affinities.json into Discover Tab API

Phase 3 — Frontend (Vineet, 1 day parallel to Phase 2)
  1. Update Discover Tab to show behavior-safe labels
  2. Add LIFT badge (2.4×) on each product card
  3. Add "Not sponsored · Available now ⚡" footer
  4. Add cohort confidence indicator
  5. Wire user switching (demo: 3 preset users with different cohorts)
```

---

## 13. The Pitch in 3 Sentences

> Amazon connects products to products.
> We connect people to people — not by asking who you are,
> but by reading what you buy.
> The math finds your group. The LIFT score finds what your group
> distinctively needs. You see it in 20 minutes.
