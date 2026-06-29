# Feature: Smart Product Comparison
## Full Architecture Design — Amazon Scale

> **Status: IMPLEMENTED (demo-grade)**
> Backend changes complete. See `04_COMPARISON_FRONTEND_SPEC.md` for frontend work.
> Audit fixes applied: decision_type, multi-cohort weight blending, pairwise ppu,
> Bayesian rating, tiebreaker reorder, safe personalization wording.

---

## 1. What's Already Built (Audit)

The comparison engine is more built than it looks. Before designing anything,
understand what exists.

### Existing `/compare` endpoint (simple)
- 5-dimension deterministic scorer: quantity_fit, price_value, delivery_speed, quality, trust
- Always produces a winner
- LLM generates 2-sentence explanation (Groq with template fallback)
- Fixed weights: qty=0.30, price=0.25, delivery=0.20, quality=0.15, trust=0.10

### Existing `/evaluate` endpoint (advanced, 7-phase pipeline)
```
Phase 1: classify_mission()     → determine occasion type → set scoring weights
Phase 2: check_constraints()    → elimination checks (budget, ETA, safety, stock)
Phase 3: compute_quantity()     → packs needed for headcount
Phase 4: compute_score()        → deterministic mission_fit_score per product
Phase 5: apply_evidence()       → community evidence adjustment
Phase 6: generate_explanation() → LLM writes the verdict sentence
Phase 7: audit_trace           → full calculation trace in response
```

### What it already does right
- Decisive winner every time (no "you decide" output)
- Constraint elimination before scoring (saves wasted scoring)
- Confidence levels: strong (gap ≥ 0.08) / moderate (≥ 0.03) / near_tie (<0.03)
- Full audit trail (calculation_trace in response)
- near_tie detection exists

### What is broken or missing
```
BROKEN:
  1. Weights are fixed by occasion type only — ignore the user entirely
     A Budget Essentials Buyer and a Premium Wellness Buyer get
     identical weights comparing the same two products.
     This is the root cause of the "value vs cheaper" friction.

  2. near_tie resolution surfaces uncertainty to the user
     When confidence == "near_tie", frontend shows "too close to call"
     or asks the user to choose. That IS the friction the mentor flagged.

  3. Comparison is stateless — no learning
     A user who always picks the cheaper option teaches the system nothing.
     Weights never adapt.

MISSING:
  4. Persona integration — cohort weights from Feature 2 not wired in
  5. Pre-computation — every comparison is computed fresh, no caching
  6. Price-per-unit normalisation — ₹49 for 10 units vs ₹89 for 25 units
     is not correctly compared (raw price comparison is misleading)
  7. Substitution awareness — when neither product is great, suggest a third
  8. Context stacking — basket state not considered (what else is in the cart?)
```

---

## 2. The Core Problem — Precisely Stated

The mentor said: "remove the friction of choosing between better value vs cheaper."

This is NOT a UI problem. It is a **missing signal** problem.

The system doesn't know whether THIS user values price or quality more.
So it either:
- Asks the user (friction)
- Uses a fixed weight for everyone (wrong for half the users)

The fix: **pull the user's price sensitivity from their behavioral cohort.**
A cohort knows whether this person has historically chosen cheaper options
or premium options. That signal replaces the question.

```
BEFORE:
  User sees: "Pick for better value" | "Pick for cheaper price"
  User makes a meta-decision before getting a recommendation.

AFTER:
  System reads: cohort = "Budget Essentials Buyer" → price_weight = 0.50
  System computes: winner with persona-adapted weights
  User sees: "Product A — ₹149 for 25 units. Better value for your budget."
  Zero question asked.
```

---

## 3. All Options for Making the Comparison Decisive

### Option A: Fixed Weights for Everyone (Current, Broken)
All users get qty=0.30, price=0.25, delivery=0.20, quality=0.15, trust=0.10.

| | |
|---|---|
| Pros | Simple. Deterministic. |
| Cons | Wrong for at least half the users. Causes "value vs cheaper" friction. |
| Verdict | ❌ What we have now. Causes the exact problem the mentor flagged. |

---

### Option B: Ask User to Set Preferences Explicitly
Before comparing, show a slider: "Price ← → Quality"

| | |
|---|---|
| Pros | Accurate. User-controlled. |
| Cons | This IS the friction. More steps, not fewer. Nobody sets sliders. |
| Verdict | ❌ Eliminated. This is the problem, not the solution. |

---

### Option C: Occasion-Type Weight Lookup (Partial fix, already exists)
`classify_mission(spec)` sets weights based on occasion type.
Birthday party → delivery=0.35 (speed matters).
Home setup → price=0.40 (budget matters more).

| | |
|---|---|
| Pros | Better than fixed. Context-aware per mission. |
| Cons | Ignores WHO the user is. Two people buying for the same occasion get same weights. |
| Verdict | ✅ Keep as baseline. Not sufficient alone. |

---

### Option D: Persona-Adapted Weights (CHOSEN — primary fix)
Merge occasion weights with cohort weights from user's behavioral profile.

```
final_weight = α × occasion_weight + (1-α) × cohort_weight
where α = 0.5 (equal blend)
```

| | |
|---|---|
| Pros | Uses real behavioral signal. No question to user. Fully automatic. |
| Cons | Requires cohort data (from Feature 2 pipeline). |
| When | Default path for known users |
| Verdict | ✅ PRIMARY APPROACH |

---

### Option E: Session-Inferred Weights
Look at current basket — if user has been picking cheaper options this session,
infer budget sensitivity for this comparison.

| | |
|---|---|
| Pros | Works for new users with no cohort. Real-time signal. |
| Cons | Short session = noisy signal. Only works mid-session. |
| When | New users / cold start |
| Verdict | ✅ Use as FALLBACK when no cohort available |

---

### Option F: Learning-to-Rank (LTR) on Comparison Outcomes
Train a LightGBM model on historical comparison choices.
Features: user cohort, product deltas, context.
Label: which product the user added to cart after comparison.

| | |
|---|---|
| Pros | Optimises for actual user behaviour. Gets better over time. |
| Cons | Needs large volume of comparison interaction data. Cold start problem. |
| At Amazon scale | This is what Amazon Personalize does in production. |
| Verdict | ✅ Production evolution. Use deterministic + persona for demo. |

---

### Option G: LLM Decides the Winner
Feed both products to LLM, ask it to pick.

| | |
|---|---|
| Pros | Flexible. Can use natural language context. |
| Cons | Non-deterministic. Can't explain the math. Expensive at scale. LLM decides → violates our architecture principle. |
| Verdict | ❌ LLM explains, never decides. |

---

### Option H: Price-Per-Unit as the Tiebreaker
When scores are within near_tie threshold, always pick lower price-per-unit.

| | |
|---|---|
| Pros | Trivially simple. Always defensible ("cheaper per use"). |
| Cons | Ignores quality, delivery, cohort. Wrong for premium buyers. |
| When | Emergency fallback only — after all other signals are exhausted. |
| Verdict | ⚠️ Last resort tiebreaker. Not the primary logic. |

---

## 4. Chosen Architecture

### 4.1 The near_tie Problem — Solved

```
CURRENT FLOW:
  score_gap < 0.03 → confidence = "near_tie" → frontend shows uncertainty

NEW FLOW:
  score_gap < 0.03 → activate tiebreaker cascade:

  Tiebreaker 1: Cohort price sensitivity
    Budget cohort (price_sensitivity = high)  → cheaper total cost wins
    Premium cohort (price_sensitivity = low)  → higher rating wins

  Tiebreaker 2: Price-per-unit
    Divide price by pack_size → lower wins
    Example: ₹89/25 units = ₹3.56/unit beats ₹49/10 units = ₹4.90/unit

  Tiebreaker 3: Delivery speed
    Amazon Now eligible → wins
    If both Now → higher stock confidence wins

  Tiebreaker 4: Return risk
    Lower return_risk wins

  Result: ALWAYS a winner. Never surfaces "too close to call" to user.
  Confidence label changes to "slight edge" for honest communication.
```

### 4.2 Persona-Adapted Weight System

**Cohort weight profiles (one per behavioral cohort from Feature 2):**

```python
COHORT_WEIGHTS = {
    "cohort_budget_essentials": {
        "price":    0.50,   # price dominates for budget buyer
        "quantity": 0.25,
        "delivery": 0.15,
        "quality":  0.10,
    },
    "cohort_premium_wellness": {
        "price":    0.10,   # quality dominates for premium buyer
        "quality":  0.50,
        "delivery": 0.25,
        "quantity": 0.15,
    },
    "cohort_baby_essentials": {
        "quality":  0.40,   # safety/quality paramount for baby products
        "delivery": 0.30,   # speed matters (running out of diapers is urgent)
        "price":    0.20,
        "quantity": 0.10,
    },
    "cohort_weekly_staples": {
        "price":    0.35,
        "quantity": 0.35,   # pack efficiency matters for bulk buyers
        "delivery": 0.20,
        "quality":  0.10,
    },
    "cohort_fitness_snack": {
        "quality":  0.45,   # ingredient quality matters
        "price":    0.25,
        "quantity": 0.20,
        "delivery": 0.10,
    },
    "cohort_party_prep": {
        "delivery": 0.45,   # speed is everything for events
        "quantity": 0.30,
        "price":    0.15,
        "quality":  0.10,
    },
    "default": {            # fallback for unknown user
        "price":    0.25,
        "quantity": 0.25,
        "delivery": 0.30,
        "quality":  0.20,
    },
}
```

**Weight blending formula:**
```python
def blend_weights(occasion_weights: dict, cohort_weights: dict, alpha=0.5) -> dict:
    """
    α = 0.5: equal blend of occasion context and user persona
    α = 0.7: occasion dominates (for strong occasion signals like birthday)
    α = 0.3: persona dominates (for generic "compare these two" without context)
    """
    return {
        dim: alpha * occasion_weights.get(dim, 0.25) +
             (1 - alpha) * cohort_weights.get(dim, 0.25)
        for dim in ["price", "quantity", "delivery", "quality"]
    }
```

### 4.3 Price-Per-Unit Normalisation (Missing, Must Add)

```
Current: compares ₹149 vs ₹89 (raw price — misleading)
Fixed:   compares ₹149/500g = ₹0.298/g vs ₹89/200g = ₹0.445/g
         → ₹149 product wins on per-unit basis despite higher sticker price

Implementation:
  price_per_unit = price / pack_size
  normalised_price_score = max(0, 1 - (price_per_unit_A / price_per_unit_B))
```

### 4.4 Substitution Engine (New)

When BOTH products score below 0.50 (neither is great), instead of showing
a bad comparison, suggest a third product.

```python
if max(score_a, score_b) < 0.50:
    return {
        "winner": None,
        "low_confidence": True,
        "suggestion": "Neither product is ideal for your goal.",
        "substitute": retrieve_best_product(category, spec),
        "substitute_score": compute_score(substitute, spec, weights),
    }
```

### 4.5 Basket Context Integration

If the user already has items in their cart, comparison weights should shift:

```
Cart contains: plates + cups + napkins (₹320 spent)
Remaining budget: ₹3680
→ price_weight automatically increases (tighter budget)
→ delivery_weight stays high (everything must arrive together)

Cart contains: balloon_pump (already in cart)
Comparing: balloon set A vs balloon set B
→ compatibility check: which is compatible with the pump already in cart?
→ compatible product gets a 0.15 bonus on final score
```

---

## 5. Full Revised System Diagram

```
User taps "Compare" on two products
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 0: Context Assembly                  │
│  - Load user's primary cohort from          │
│    user_cluster_map.json                    │
│  - Load cohort weight profile               │
│  - Load current basket state                │
│  - Extract occasion + headcount + budget    │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 1: Weight Computation                │
│  - Get occasion_weights from classifier     │
│  - Get cohort_weights from persona profile  │
│  - Blend: final_weights = blend(α=0.5)      │
│  - Adjust for basket state                  │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 2: Hard Constraint Elimination       │
│  (unchanged from current)                   │
│  - Budget: can user afford packs needed?    │
│  - Delivery: can it arrive before deadline? │
│  - Safety: any banned safety tags?          │
│  - Stock: is it available?                  │
│  Result: eliminate, or proceed to scoring   │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 3: Normalised Scoring                │
│  Dimensions:                                │
│  - price_per_unit (NEW — not raw price)     │
│  - quantity_fit (packs for headcount)       │
│  - delivery_speed (ETA score)               │
│  - quality (rating + return_risk)           │
│  - basket_compatibility (NEW)               │
│                                             │
│  weighted_score = Σ(dimension × weight)     │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 4: Winner Determination              │
│  gap = |score_a - score_b|                  │
│                                             │
│  gap ≥ 0.08 → "clear winner" (strong)       │
│  gap ≥ 0.03 → "slight edge" (moderate)      │
│  gap < 0.03 → TIEBREAKER CASCADE (never     │
│               show uncertainty to user)     │
│    TB1: cohort price sensitivity            │
│    TB2: price per unit                      │
│    TB3: delivery speed                      │
│    TB4: return risk                         │
│  Result: always a winner, always a label    │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 5: Low Score Substitution Check      │
│  If max(score_a, score_b) < 0.50:           │
│    → suggest a better third product         │
│    → "Neither is ideal. Here's a better     │
│       option for your goal."                │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 6: Evidence Boost                    │
│  (unchanged from current)                   │
│  Community adoption rate for the occasion   │
│  adjusts final score slightly               │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 7: LLM Explanation                   │
│  Input: winner, loser, dominant_factor,     │
│          user cohort label, context         │
│  Output: 2 sentences. Decisive. Specific.   │
│  Example:                                   │
│  "Pampers Premium wins for your weekly      │
│   baby-care basket — ₹3.56/unit vs ₹4.90/  │
│   unit for Huggies, and it arrives in 20    │
│   min. Given your replenishment pattern,    │
│   the value gap compounds every cycle."     │
│                                             │
│  LLM explains the decision.                 │
│  LLM does NOT make the decision.            │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  PHASE 8: Feedback Logging                  │
│  Log: which winner was shown                │
│       did user add to cart?                 │
│       did user override? (picked the loser) │
│  Use to: calibrate cohort weights over time │
└─────────────────────────────────────────────┘
```

---

## 6. The Decisive Verdict UI Contract

The comparison response MUST conform to this contract.
Frontend renders based on this. No "you choose" anywhere.

```json
{
  "winner": "a",
  "confidence": "clear_winner | slight_edge | substitution_suggested",
  "verdict_headline": "Product A wins for your goal",
  "verdict_reason": "₹3.56/unit vs ₹4.90/unit. Arrives in 20 min.",
  "explanation": "2-sentence LLM explanation personalised to cohort.",
  "dominant_factor": "price_per_unit | delivery | quantity | quality",
  "persona_signal": "Budget replenishment pattern → price weighted at 50%",
  "score_a": { "total": 0.74, "price_per_unit": 3.56, ... },
  "score_b": { "total": 0.61, "price_per_unit": 4.90, ... },
  "comparison_rows": [
    { "label": "Price per unit", "a": "₹3.56/unit", "b": "₹4.90/unit", "winner": "a" },
    { "label": "Pack value",     "a": "₹149 / 42 units", "b": "₹89 / 18 units", "winner": "a" },
    { "label": "Delivery",       "a": "⚡ 20 min", "b": "⚡ 20 min", "winner": "tie" },
    { "label": "Rating",         "a": "4.3★", "b": "4.1★", "winner": "a" }
  ],
  "substitute": null,
  "add_winner_to_cart": { "asin": "B0INxxx", "packs": 2 },
  "simulated_data": true,
  "audit_trace_id": "uuid"
}
```

**What the UI does with this:**
- Shows verdict_headline in large text at the top
- Shows winner product highlighted, loser dimmed
- Shows comparison_rows as a simple table
- Shows explanation as a card below
- Shows "Add Product A to Cart" as the primary CTA
- NEVER shows a "which do you prefer?" prompt

---

## 7. At Amazon Scale

### 7.1 The Scale Problem

```
Amazon Now India:
  Daily active users:     30M
  Product comparisons:    ~5M per day
  Unique product pairs:   ~50B possible pairs (300M × 300M / 2)
  Active category pairs:  ~500K (realistic comparable pairs)
```

### 7.2 Pre-Computation Strategy

Don't compute comparisons at request time for popular pairs.

```
TIER 1 — Pre-computed, cached in Redis (top 10K pairs per category)
  Frequency: Weekly rebuild
  Coverage: ~80% of all comparisons
  Latency: <5ms (Redis GET)
  Key: "compare:{cohort_id}:{asin_a}:{asin_b}"

TIER 2 — Computed at request time, cached after first hit (long-tail pairs)
  Frequency: On first request, then cached 24h
  Coverage: ~18% of comparisons
  Latency: <80ms (fast deterministic scorer)
  Key: same Redis schema

TIER 3 — Real-time, no cache (extremely rare pairs, new products)
  Coverage: ~2% of comparisons
  Latency: <200ms (acceptable)
  No caching (would pollute cache with noise)
```

### 7.3 Infrastructure

| Component | Technology | Why |
|---|---|---|
| Comparison cache | Redis Cluster | Sub-5ms, 200M key capacity |
| Pre-computation | AWS Lambda (scheduled) | Serverless, cost-efficient for batch |
| Weight store | DynamoDB (cohort_id → weights) | Single-digit ms, managed |
| Feedback stream | Kafka | Capture override events for weight calibration |
| LTR model serving | SageMaker endpoint | For production ML ranker |
| A/B testing | Amazon CloudWatch + feature flags | Test weight configurations |

### 7.4 Weight Calibration Loop (Production)

```
User compares A vs B
System recommends A
User adds B to cart instead (override)
                │
                ▼
Kafka event: {
  user_id, cohort_id, winner_shown: "a", user_chose: "b",
  score_gap: 0.04, dominant_factor: "price",
  product_a_price_per_unit: 3.56, product_b_price_per_unit: 4.90
}
                │
                ▼
Weekly batch job:
  For each cohort: count overrides by dominant_factor
  If cohort X overrides "price wins" 40% of the time:
    → increase quality_weight for cohort X
    → decrease price_weight
  Update cohort weight profiles in DynamoDB
```

---

## 8. Option Comparison Summary

| Option | Decisive? | Persona-aware? | Scale? | Demo? | Verdict |
|---|---|---|---|---|---|
| Fixed weights | ✅ | ❌ | ✅ | ✅ | Current broken state |
| Ask user | ❌ | Sort of | ✅ | ❌ | The exact friction to remove |
| Occasion-type weights | ✅ | Partial | ✅ | ✅ | Baseline, keep |
| Persona-adapted weights | ✅ | ✅ | ✅ | ✅ | **PRIMARY** |
| Session-inferred | ✅ | ✅ | ✅ | ⚠️ | Fallback |
| LTR model | ✅ | ✅ | ✅ | ❌ | Production evolution |
| LLM decides | ❌ | Sort of | ❌ | ❌ | Never |
| Price-per-unit tiebreaker | ✅ | ❌ | ✅ | ✅ | Last resort |

---

## 9. What Changes in the Code

### 9.1 New: `cohort_weights.json`
```json
{
  "cohort_budget_05": { "price": 0.50, "quantity": 0.25, "delivery": 0.15, "quality": 0.10 },
  "cohort_premium_10": { "price": 0.10, "quality": 0.50, "delivery": 0.25, "quantity": 0.15 },
  "default": { "price": 0.25, "quantity": 0.25, "delivery": 0.30, "quality": 0.20 }
}
```

### 9.2 Modified: `scorer.py`
- Add `price_per_unit` as a scoring dimension
- Accept `cohort_weights` parameter in `compute_score()`
- Blend occasion + cohort weights

### 9.3 Modified: `engine.py`
- Phase 0: load user cohort from `user_cluster_map.json`
- Phase 1: blend weights (occasion + cohort)
- Phase 4: replace near_tie with tiebreaker cascade (never surface uncertainty)
- Phase 5: add substitution check
- Phase 8: add feedback log stub

### 9.4 Modified: `comparison.py` router
- Accept `user_id` in `/compare` request
- Pass cohort_id to engine
- Add `/compare/feedback` endpoint for override logging

---

## 10. Demo Flow

```
Judge demo: two Maggi variants — "Masala 4-pack ₹68" vs "Atta Noodles 4-pack ₹72"

User A (Budget Essentials cohort):
  price_weight = 0.50
  Winner: Masala (₹17/pack) over Atta (₹18/pack)
  Verdict: "Masala wins — ₹17/pack vs ₹18/pack. Same delivery."

User B (Premium Wellness cohort):
  quality_weight = 0.50
  Winner: Atta (4.3★, whole wheat) over Masala (4.1★)
  Verdict: "Atta Noodles wins — higher fibre, better rated.
            ₹1/pack difference is negligible for your basket."

Same two products. Same comparison request.
Completely different winners. No question asked.
That is the demo moment.
```

---

## 11. The Pitch in 3 Sentences

> Most comparison tools make YOU decide what matters — price or quality.
> We already know from your shopping pattern that you care more about value-per-unit.
> So we just tell you the answer.
