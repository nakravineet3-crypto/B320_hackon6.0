# Feature: Adaptive Reorder & Depletion Intelligence
## Full Architecture Design — Amazon Scale

> **Status: IMPLEMENTED (demo-grade)**
> Backend: `/reorder/suggestions` endpoint with EWMA, seasonal, lifecycle, cold-start.
> Frontend spec at bottom of this document.

---

## 1. What's Wrong With the Current System

The existing depletion model stores `average_interval_days` — a simple mean.
That's the wrong model for three reasons:

```
Problem 1: Static average ignores trends
  User started ordering diapers every 30 days.
  Now orders every 22 days (child growing, using more).
  Simple average says 26 days. Reality is 22. User runs out.

Problem 2: No seasonal awareness
  User buys 1kg sugar every 30 days. Diwali is in 12 days.
  System says: next reorder in 18 days. But they need 4kg for Diwali.
  System gives no signal.

Problem 3: No lifecycle awareness
  User has ordered Size S diapers for 4 months.
  70% of parents at this stage switch to Size M.
  System keeps recommending Size S. Parent discovers the problem themselves.

Problem 4: New users get nothing
  0 purchase history → 0 reorder suggestions.
  But a new user in Bangalore with household_size=4 and new_parent tag
  can get sensible defaults from similar users immediately.
```

---

## 2. Feature Scope — When Does It Activate

### 2.1 Entry Conditions Per User

| User State | What They See | Data Source |
|---|---|---|
| 0 orders, opted in via questionnaire | "Potential Regulars" — cohort defaults, labeled as estimated | Cohort + city defaults |
| 1st order placed | Immediate next-alert scheduled | City+category median interval |
| 2–5 orders same category | Blended alert (70% cohort, 30% personal) | Partial personal history |
| 5–10 orders | Mostly personal, cohort as sanity check | Personal EWMA |
| 10+ orders | Full personal model | EWMA + seasonal + lifecycle |
| Baby/childcare products | Lifecycle stage tracking active | Purchase timeline |

### 2.2 Entry Points Into the Feature

```
1. ACTIVE ALERT (push notification)
   Trigger: days_remaining ≤ reorder_threshold for user's cohort
   Message: "Your Amul Milk runs out tomorrow. Reorder 6 bottles?"
   Action: one-tap reorder or snooze

2. HOME SCREEN SECTION
   Trigger: any item with days_remaining ≤ 5
   Render: "Running Low" horizontal scroll row
   Priority order: most urgent first

3. CART INJECTION
   Trigger: user starts a mission cart, any depleting items overlap with cart categories
   Message: "2 of your regulars are also running low. Add them?"
   Smart: only inject if total stays within budget

4. BASKET COMPLETION CHECK
   Trigger: cart is ready to place, check for items due within 3 days
   Message: "Don't forget: your Maggi runs out in 2 days."

5. WEEKLY DIGEST (Monday morning)
   Trigger: scheduled, every Monday 9am
   Content: "This week's replenishment — 4 items due"

6. FESTIVE EARLY WARNING
   Trigger: 3 weeks before any major Indian occasion in user's history
   Message: "Diwali in 21 days. Your usual sugar won't be enough this year."

7. LIFECYCLE ALERT (no time trigger — event trigger)
   Trigger: lifecycle stage transition detected
   Message: "Most parents switch to Size M diapers around this stage. Ready to try?"
```

### 2.3 Minimum Viable Activation

A user sees reorder suggestions if ANY of these are true:
- They have completed ≥ 2 orders of the same product
- They have ≥ 5 total orders (enough to infer category cadences)
- They explicitly set up "My Regulars" (opt-in, works with 0 history)
- They belong to a cohort with known default cadences AND their city is known

---

## 3. The Core Depletion Model

### 3.1 EWMA — Exponential Weighted Moving Average

Replace static `average_interval_days` with an adaptive learner.

```python
α = 0.3   # Recency weight — recent orders matter more than old ones
          # Higher α = faster adaptation, lower α = more stable

def update_ewma(old_interval: float, new_observation: float) -> float:
    return α * new_observation + (1 - α) * old_interval
```

Why EWMA over simple average:
```
Order history (days between orders): [30, 28, 29, 25, 22, 21]

Simple average: 25.8 days → suggests reorder in 26 days
EWMA (α=0.3):  works backwards: 21.8 days → suggests reorder in 22 days

EWMA correctly captures the trend: this person is ordering more frequently.
The simple average is always behind.
```

**Variance tracking** — how consistent is the user?

```python
def update_variance(old_variance: float, old_mean: float, new_obs: float) -> float:
    return (1 - α) * (old_variance + α * (new_obs - old_mean) ** 2)

# High variance → lower confidence → wider reorder window → notify earlier
# Low variance → high confidence → tight reorder window → notify right on time
```

**Confidence model:**

```python
confidence_score = min(1.0, purchase_count / 10) * (1 / (1 + normalized_variance))

if confidence_score >= 0.8: label = "high"
elif confidence_score >= 0.5: label = "medium"
else: label = "low"
```

### 3.2 Cohort-Aware Reorder Thresholds

Different user types have different tolerance for running out.

```python
COHORT_REORDER_THRESHOLDS = {
    "cohort_baby_essentials":   10,  # Never run out of diapers
    "cohort_premium_wellness":   7,  # Comfortable buffer
    "cohort_weekly_staples":     5,  # Order weekly, 5 days warning
    "cohort_budget_essentials":  3,  # Order tight, low margin
    "cohort_fitness_snack":      4,
    "cohort_party_prep":         7,  # Event-based, needs buffer
    "default":                   5,
}
```

**Urgency labels** (based on days_remaining vs threshold):

```
days_remaining > threshold × 1.5 → "upcoming"    (show in weekly digest only)
days_remaining ≤ threshold × 1.5 → "due_soon"    (show in home section)
days_remaining ≤ threshold        → "reorder_now" (push notification)
days_remaining ≤ 1               → "urgent"       (prominent alert)
days_remaining ≤ 0               → "overdue"      (assume they've run out)
```

---

## 4. Seasonal Adjustment Layer

### 4.1 Indian Festive Calendar

```python
SEASONAL_EVENTS = {
    "diwali": {
        "approx_month": 10,   # October/November (varies by year)
        "category_boosts": {
            "sweetener":       4.0,   # Sugar ×4
            "edible_oils":     3.0,   # Ghee ×3
            "dry_fruits":      5.0,   # Cashews, almonds ×5
            "candles":        10.0,   # If they buy candles, 10×
            "pooja_items":     3.0,
            "gifting":         6.0,
        },
        "boost_window_days": 30,  # Starts 30 days before
    },
    "holi": {
        "approx_month": 3,
        "category_boosts": {
            "sweetener": 3.0,
            "dairy":     2.0,   # Thandai ingredients
        },
        "boost_window_days": 14,
    },
    "navratri": {
        "approx_month": 10,
        "category_boosts": {
            "fasting_staples": 3.0,   # Sabudana, singhara flour
            "fruits":          2.0,
            "dairy":           1.5,
        },
        "boost_window_days": 10,
    },
    "eid": {
        "approx_month": 4,  # Varies
        "category_boosts": {
            "biryani_staples": 4.0,
            "sweetener":       3.0,
            "vermicelli":      8.0,   # Sewai
        },
        "boost_window_days": 14,
    },
    "monsoon": {
        "months": [6, 7, 8, 9],
        "category_boosts": {
            "hot_beverages":   2.0,
            "medicines":       1.5,
            "ginger_garlic":   1.5,
        },
        "duration_based": True,  # Not event-based, duration-based
    },
    "school_year_start": {
        "approx_month": 6,
        "category_boosts": {
            "stationery":     3.0,
            "snacks":         1.5,
        },
        "boost_window_days": 21,
    },
}
```

### 4.2 Seasonal Multiplier Calculation

```python
def seasonal_multiplier(category: str, date: datetime, user_city: str) -> tuple[float, str | None]:
    """
    Returns (multiplier, event_name).
    Multiplier ramps up linearly as event approaches, peaks at event day.
    """
    for event_name, event in SEASONAL_EVENTS.items():
        if category not in event["category_boosts"]:
            continue

        boost = event["category_boosts"][category]
        window = event.get("boost_window_days", 14)

        if event.get("duration_based"):
            # Monsoon-style — active for entire month range
            if date.month in event["months"]:
                return boost, event_name
            continue

        event_date = _next_occurrence(event["approx_month"], date)
        days_until = (event_date - date).days

        if 0 <= days_until <= window:
            # Linear ramp: 0 at window start, full boost at event day
            decay = 1.0 - (days_until / window)
            effective_boost = 1.0 + (boost - 1.0) * decay
            return round(effective_boost, 2), event_name

    return 1.0, None
```

### 4.3 How Seasonal Affects the Reorder Suggestion

```
Normal:   User needs 1kg sugar every 30 days → next order in 18 days
Diwali:   Diwali is 12 days away. Category boost = 4×

Adjusted quantity: 1kg × 4 = 4kg
Adjusted reorder window: urgent now (not in 18 days)

Explanation shown to user:
"Your usual sugar order is 1kg every 30 days.
 Diwali is 12 days away — you'll likely need 4kg this year.
 Order now to arrive before the festivities."
```

---

## 5. Lifecycle Change Detection

### 5.1 The Diaper Problem — and the General Framework

```
LIFECYCLE_CATEGORIES = {
    "diapers": {
        "stages": ["Newborn_NB", "Small_S", "Medium_M", "Large_L", "XLarge_XL",
                   "PantsM", "PantsL", "PantsXL"],
        "typical_duration_months": [1, 2, 3, 4, 4, 4, 4, 4],
        "exit_signal": "potty_training_category_purchase",  # user buys potty seat → stop diapers
        "transition_threshold": 0.55,  # 55% of similar users have transitioned
    },
    "baby_formula": {
        "stages": ["Stage1_0-6m", "Stage2_6-12m", "Stage3_12-24m"],
        "typical_duration_months": [6, 6, 12],
        "exit_signal": "cow_milk_category_purchase",
        "transition_threshold": 0.60,
    },
    "baby_food_purees": {
        "stages": ["4-6m", "6-9m", "9-12m"],
        "typical_duration_months": [3, 3, 3],
        "exit_signal": "family_food_purchase_pattern",
        "transition_threshold": 0.65,
    },
}
```

### 5.2 Lifecycle Detection Algorithm

```python
def check_lifecycle_transition(
    user_id: str,
    category: str,
    current_stage: str,
    first_order_date: date,
) -> LifecycleSignal | None:

    if category not in LIFECYCLE_CATEGORIES:
        return None

    config = LIFECYCLE_CATEGORIES[category]
    stage_idx = config["stages"].index(current_stage)
    months_in_category = (today - first_order_date).days / 30

    # Expected duration in this stage
    expected_duration = sum(config["typical_duration_months"][:stage_idx + 1])

    if months_in_category < expected_duration * 0.75:
        return None  # Too early to transition

    # Check next stage exists
    if stage_idx + 1 >= len(config["stages"]):
        # End of lifecycle — check exit signal
        return check_exit_signal(user_id, config["exit_signal"])

    next_stage = config["stages"][stage_idx + 1]

    # Community signal: what fraction of similar users have already transitioned?
    community_rate = get_community_transition_rate(
        category, current_stage, months_in_category
    )

    if community_rate >= config["transition_threshold"]:
        return LifecycleSignal(
            signal_type="size_up",
            current_stage=current_stage,
            suggested_stage=next_stage,
            community_rate=community_rate,
            message=_lifecycle_message(category, current_stage, next_stage, community_rate),
        )

    return None

def _lifecycle_message(category, current, next_stage, rate):
    pct = int(rate * 100)
    return (
        f"{pct}% of parents at this stage have already switched "
        f"from {current} to {next_stage} diapers. Ready to try?"
    )
```

### 5.3 Observable Lifecycle Signals (without explicit age data)

We never ask the user how old their child is. We infer from behavior:

```
Signal 1: Time elapsed since first order of lifecycle product
  first_order_date captured on first purchase → months_since = proxy for child age

Signal 2: Search/browse behavior (production only)
  User searched "size M diapers" → strong transition signal

Signal 3: Rejection signal
  User dismissed "reorder Size S" three times → possible dissatisfaction signal

Signal 4: Community pattern (available from simulated data)
  P(transition to Size M | ordering Size S for X months) from cohort data
```

---

## 6. Cold Start — New Users Get Useful Suggestions From Day 1

### 6.1 The Four Tiers

**Tier 0 — Zero orders, opted-in via questionnaire**
```
Show: "Set up your regulars" onboarding
User selects 3-5 categories they buy regularly
System shows: top 3 products per category for their city
Labels clearly: "Estimated — based on similar households in [city]"
```

**Tier 1 — 1st order placed (just occurred)**
```
Trigger: immediately after first order completes
Action: schedule next depletion alert
Source: city + category cohort median interval

Example:
  User in Bangalore orders Amul Milk 1L × 6
  Cohort median for dairy in Bangalore: 3 days
  → Schedule milk alert for Day 2 (threshold = 1 day before median)
  → Show: "Your milk order was delivered. We'll remind you in 2 days."
```

**Tier 2 — 2–5 orders (pattern emerging)**
```
Blend formula:
  interval = 0.7 × cohort_median + 0.3 × personal_mean
  confidence = "medium"
  label: "Based on your first few orders"
```

**Tier 3 — 5–10 orders (personal model dominant)**
```
  interval = 0.3 × cohort_median + 0.7 × personal_ewma
  confidence = "high"
  label: "Based on your order history"
```

**Tier 4 — 10+ orders (full personal)**
```
  interval = personal_ewma (cohort only for anomaly detection)
  confidence = "high"
  No label shown — it's just "your usual"
```

### 6.2 City-Category Default Cadences

```json
{
  "dairy": {
    "Bangalore": 3.0,
    "Mumbai": 2.5,
    "Delhi": 3.5,
    "Chennai": 3.0,
    "default": 3.5
  },
  "grocery_staples": {
    "default": 14.0
  },
  "cooking_oil": {
    "default": 30.0
  },
  "diapers": {
    "default": 20.0
  },
  "personal_care": {
    "default": 30.0
  }
}
```

### 6.3 FAISS Cold Start (Production)

For new users, use FAISS nearest-neighbor to find the most similar existing users
based on profile features and inherit their cadence model.

```
Profile feature vector:
  [city_encoding, household_size, age_bracket, monthly_budget, prime_member, occasions_per_year]

FAISS search: top-5 most similar users
Aggregate their cadence models → initial baseline for new user
```

---

## 7. Feature Integration Map

### 7.1 With Identity Groups (Feature 2)

```
Cohort → Reorder Threshold
  Baby Essentials Buyer: never run out → threshold = 10 days
  Budget Essentials Buyer: reorder tight → threshold = 3 days
  Premium Wellness Buyer: comfortable buffer → threshold = 7 days

Cohort → Cold Start Default
  New user assigned to "Weekly Staples Buyer" cohort
  → Inherits that cohort's category cadences as Day 1 defaults

Cohort → Seasonal Sensitivity
  Party Prep Buyer: boost ALL seasonal events (they always buy for occasions)
  Budget Essentials: boost only when seasonal category overlaps with regulars
```

### 7.2 With Comparison (Feature 3)

```
Reorder trigger fires for Product X
System checks: is there a competitor in same category with PPU gap > 15%?

YES → Comparison mode:
  "Your Parle-G is running low. Britannia Marie has 18% better value/unit. Compare?"
  → Launches comparison screen with pre-filled products

NO → Direct reorder:
  "Your Parle-G is running low. Reorder 2 packs?"
  → One-tap reorder, no comparison friction

Why PPU threshold of 15%? Below that, switching cost (finding the alternative,
reading reviews) exceeds the savings for most users.
```

### 7.3 With Cart Builder (Feature 1)

```
User starts: "Groceries for next week" mission cart

Step 1 (Cart Builder): Collects mission context (headcount=4, budget=₹2000, deadline=48h)

Step 2 (Reorder Integration):
  Query: which of user's regulars are due within 7 days?
  Result: Milk (1 day), Sugar (3 days), Oil (6 days)

Step 3 (Budget Check):
  Existing cart total: ₹1,200
  Adding regulars: Milk ₹168 + Sugar ₹40 + Oil ₹130 = ₹338
  Total: ₹1,538 — within budget ✓

Step 4 (Injection):
  Show: "3 of your regulars are also due this week. Add them? +₹338"
  [Add All] [Review] [Skip]
```

### 7.4 With Occasion History

```
User's occasion_history shows: repeat_next_year = true for Diwali
days_until_recurrence = 128 days (currently)

At 21 days before:
  Scan user's regular purchases for Diwali-boost categories
  Sugar: user buys 1kg/month → estimate 4kg for Diwali
  Ghee: user buys 500g/month → estimate 1.5kg for Diwali

Early Warning Alert (3 weeks before):
  "Diwali 2026 is 21 days away.
   Last year you spent ₹4,203 on Diwali shopping.
   Your sugar and ghee supplies won't last through Diwali.
   Start your Diwali prep cart?"
```

---

## 8. Full System Diagram

```
ORDER EVENT
(any purchase)
     │
     ▼
┌───────────────────────────────────────────┐
│  INGESTION LAYER                          │
│  Capture: user_id, product, qty, date,    │
│  interval_since_last_order                │
│  Production: Kafka stream                 │
│  Demo: purchase_history.json              │
└───────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────┐
│  EWMA UPDATER                             │
│  Update interval estimate for this        │
│  (user, product) pair                     │
│  Update variance → update confidence      │
│  Write to: DynamoDB (prod) / JSON (demo)  │
└───────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────┐
│  LIFECYCLE CHECKER                        │
│  Is this a lifecycle category?            │
│  Check months_in_stage vs community rate  │
│  Emit: LifecycleSignal if threshold met   │
└───────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────┐
│  DEPLETION WINDOW CALCULATOR              │
│  base_interval = EWMA estimate            │
│  seasonal_multiplier = f(category, date)  │
│  adjusted_quantity = normal_qty × seasonal│
│  days_remaining = interval - days_since   │
│  urgency = f(days_remaining, cohort_threshold) │
└───────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────┐
│  COMPARISON OPPORTUNITY CHECK             │
│  Is there a better alternative at PPU     │
│  gap > 15%? → flag for comparison         │
│  Otherwise → direct reorder               │
└───────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────┐
│  RANKED SUGGESTION LIST                   │
│  Sort by urgency, then seasonal priority, │
│  then user preference signal              │
│  Limit: top 8 items per user per session  │
└───────────────────────────────────────────┘
     │
     │          ┌──────────────────────────┐
     │          │  COLD START PATH         │
     │          │  If user has < 2 orders  │
     │          │  for a product:          │
     │          │  Use cohort defaults     │
     │          │  Label as "estimated"    │
     │          └──────────────────────────┘
     ▼
┌───────────────────────────────────────────┐
│  /reorder/suggestions RESPONSE            │
│  Each item:                               │
│  - days_remaining, urgency                │
│  - adjusted_quantity (incl. seasonal)     │
│  - seasonal_context (event name, boost)   │
│  - lifecycle_signal (size_up etc)         │
│  - comparison_opportunity flag            │
│  - cold_start (bool)                      │
│  - confidence, explanation                │
└───────────────────────────────────────────┘
```

---

## 9. At Amazon Scale

### 9.1 Scale Numbers

```
200M active users in India (target)
× 50 regularly purchased products per user
= 10B depletion windows to maintain

Peak event rate: 50K orders/second during Diwali sales
Depletion window updates per second: 50K (1:1 with orders)
```

### 9.2 Tiered Computation

| Tier | Trigger | Latency | Tech |
|---|---|---|---|
| Pre-computed | Daily batch | 0ms (cache hit) | EMR + Redis |
| Event-driven | On order | <100ms | Lambda + DynamoDB |
| Real-time | On app open | <5ms | Redis sorted set |

**Redis Sorted Set Schema:**
```
Key:   reorder:user:{user_id}
Score: unix_timestamp of next_depletion_date
Value: asin:quantity:urgency_level

Query on app open:
  ZRANGEBYSCORE reorder:user:U001 {now} {now + 7days}
  → returns all items depleting in next 7 days, sorted by urgency
  → < 5ms
```

**DynamoDB Schema:**
```
PK: USER#{user_id}
SK: PRODUCT#{asin}

Attributes:
  ewma_interval: float
  ewma_variance: float
  purchase_count: int
  last_order_date: str
  lifecycle_stage: str | null
  lifecycle_first_order: str | null
  cohort_id: str
  confidence: str
```

**Seasonal Update (weekly Lambda):**
```python
def apply_seasonal_update(category: str, boost: float, window_days: int):
    # Scan DynamoDB for all users who regularly buy this category
    # Adjust their Redis sorted set score (next_depletion) forward
    # by the seasonal urgency (earlier alert + larger quantity)
```

### 9.3 The Feedback Loop

```
User receives alert: "Your milk runs out tomorrow"

Case A — User reorders immediately:
  Signal: interval model is accurate
  Action: no change to EWMA (observation confirms prediction)

Case B — User snoozes (already have stock):
  Signal: model is over-estimating frequency
  Action: increase EWMA interval by 10% for next cycle

Case C — User ignores (already ran out, bought locally):
  Signal: model is under-estimating frequency
  Action: Captured indirectly — next order comes earlier than predicted
          EWMA will self-correct on the next order

Case D — User changes quantity:
  Signal: quantity preference is changing
  Action: update suggested_quantity for next alert
```

---

## 10. The Adaptive Quantity Model

Beyond when to reorder — how much to suggest.

```python
def suggested_quantity(
    product: dict,
    user_ewma: dict,
    seasonal_multiplier: float,
    historical_quantity: int,
) -> dict:
    base_qty = historical_quantity  # what they usually order

    # Seasonal adjustment
    seasonal_qty = math.ceil(base_qty * seasonal_multiplier)

    # Lifecycle adjustment (e.g., diapers: child growing = more units/day)
    if user_ewma.get("lifecycle_stage"):
        stage_factor = _lifecycle_quantity_factor(user_ewma["lifecycle_stage"])
        lifecycle_qty = math.ceil(seasonal_qty * stage_factor)
    else:
        lifecycle_qty = seasonal_qty

    return {
        "suggested_quantity": lifecycle_qty,
        "base_quantity": base_qty,
        "seasonal_boost": seasonal_multiplier > 1.0,
        "seasonal_multiplier": seasonal_multiplier,
        "lifecycle_adjustment": lifecycle_qty != seasonal_qty,
        "explanation": _quantity_explanation(base_qty, lifecycle_qty, seasonal_multiplier),
    }
```

---

## 11. Demo Script

### Scenario A — Adaptive Interval (vs static average)
```
User U001 has been ordering diapers:
  June 1: Size S × 60
  June 22: Size S × 60  (21-day gap)
  July 10: Size S × 60  (18-day gap)
  July 25: Size S × 60  (15-day gap — accelerating)

Static average says: (21+18+15)/3 = 18 days
EWMA (α=0.3) says: 15.6 days → correctly tracks the trend

Demo: show the depletion estimate is 3 days earlier with EWMA
      and that they'd have run out under the static model
```

### Scenario B — Lifecycle Alert
```
User has ordered Size S diapers since April.
Current: late June → 2.5 months elapsed.
Community data: 62% of parents switch from S to M around month 3.
62% > 55% threshold.

Alert: "62% of parents at this stage have switched to Size M.
        Ready to try? We'll add one pack to compare."
```

### Scenario C — Seasonal Boost
```
Demo date: set to October 1 (Diwali is ~3 weeks away).
User buys 1kg sugar every 25 days.

Normal: next order in 12 days. Quantity: 1kg.
Seasonal: Diwali in 20 days. Boost: 3.5× (ramping).

Alert: "Diwali is 20 days away. Your usual 1kg won't be enough.
        This year you might need 3.5kg. Order now?"
```

### Scenario D — Cold Start
```
New user, 0 purchase history, Bangalore, household_size=4.
Sets up: selects "Dairy, Grocery Staples, Snacks" in questionnaire.

Immediate suggestions:
  Amul Milk 1L (dairy default: 3 days) — "Estimated for your household"
  Aashirvaad Atta 5kg (staples default: 25 days) — "Estimated"
  Parle-G 800g (snacks default: 7 days) — "Estimated"

After first milk order → schedules real alert
After 5 milk orders → switches to personal EWMA, drops "Estimated" label
```

---

## 12. What NOT to Build for Demo

**Do not build:**
- Kafka stream (document in pitch as production component)
- DynamoDB migration (use JSON files)
- Redis sorted set (compute on request, acceptable for demo scale)
- FAISS cold start neighbor search (use simple city+category lookup)
- Real-time order event webhooks (trigger on API call)

**Build only:**
- EWMA computation from purchase_history.json
- Seasonal multiplier lookup (hardcoded Indian calendar)
- Lifecycle stage detection for diaper category
- Cold start tiers (order count-based branching)
- `/reorder/suggestions` endpoint with full rich response
- `/reorder/feedback` stub for snooze/override signals

---

## 13. Frontend Spec (for Vineet)

### API Endpoint
```
GET /reorder/suggestions?user_id=U001
```

### Response shape per item
```json
{
  "items": [
    {
      "asin": "MC_MILK_001",
      "title": "Amul Milk 1L",
      "category": "dairy",
      "days_remaining": 1.2,
      "urgency": "urgent",
      "suggested_quantity": 6,
      "base_quantity": 6,
      "price": 28,
      "amazon_now_eligible": true,
      "confidence": "high",
      "cold_start": false,
      "ewma_interval": 3.1,
      "last_purchased": "2026-06-28",
      "seasonal_context": null,
      "lifecycle_signal": null,
      "comparison_opportunity": null,
      "explanation": "You usually order every 3 days. Running out tomorrow."
    },
    {
      "asin": "MC_SUGAR_001",
      "title": "Tata Sugar 1kg",
      "category": "sweetener",
      "days_remaining": 6,
      "urgency": "reorder_now",
      "suggested_quantity": 4,
      "base_quantity": 1,
      "price": 44,
      "amazon_now_eligible": true,
      "confidence": "high",
      "cold_start": false,
      "seasonal_context": {
        "event": "diwali",
        "days_until_event": 20,
        "multiplier": 3.5,
        "message": "Diwali is 20 days away — you'll likely need 3.5kg this year."
      },
      "lifecycle_signal": null,
      "comparison_opportunity": null,
      "explanation": "Running low AND Diwali is coming. Order 4kg now."
    },
    {
      "asin": "MC_DIAPERS_S",
      "title": "Pampers Size S × 60",
      "category": "diapers",
      "days_remaining": 8,
      "urgency": "reorder_now",
      "suggested_quantity": 2,
      "price": 649,
      "confidence": "high",
      "cold_start": false,
      "seasonal_context": null,
      "lifecycle_signal": {
        "signal_type": "size_up",
        "current_stage": "Small_S",
        "suggested_stage": "Medium_M",
        "community_rate": 0.62,
        "message": "62% of parents at this stage have switched to Size M."
      },
      "comparison_opportunity": null,
      "explanation": "Running low in 8 days. Also — most parents try Size M around now."
    }
  ],
  "meta": {
    "user_id": "U001",
    "cold_start_tier": 4,
    "total_items": 8,
    "urgent_count": 2,
    "seasonal_events_active": ["diwali"],
    "generated_at": "2026-06-30T10:00:00"
  }
}
```

### UI Rendering Rules

**Urgency → visual treatment:**
| urgency | Card border | Badge | Notification |
|---|---|---|---|
| `urgent` | Red border | "Running Out" red badge | Push sent |
| `reorder_now` | Orange border | "Order Now" orange badge | In-app |
| `due_soon` | Yellow border | "Due Soon" | In home section |
| `upcoming` | No border | No badge | Weekly digest only |

**Seasonal context:** Show a 🪔 icon with event name. Quantity displayed as
"4kg (Diwali: usual 1kg × 3.5)" with the seasonal reason.

**Lifecycle signal:** Show as a separate card below the reorder card:
"Most parents try Size M now. [Try one pack?]" — secondary action, not primary.

**Cold start items:** Show with a "~" prefix on quantity: "~6 units (estimated)"
and a note: "Based on typical households in Bangalore."

**Comparison opportunity:** When `comparison_opportunity` is set, the primary
CTA changes from "Reorder" to "Better deal spotted → Compare".

### Sort order
1. `urgent` first
2. Has `seasonal_context` with `days_until_event < 14`
3. Has `lifecycle_signal`
4. `reorder_now`
5. `due_soon`
6. `upcoming`
