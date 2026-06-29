# MissionCart — Cart Building Stress Test Prompt for Codex

## Context

You are testing the MissionCart backend — a FastAPI application running at `http://localhost:8000`.

The cart building system (`POST /api/mission/build`) takes a natural-language goal and budget, routes through an LLM goal parser, a domain/occasion router, a 6-stage cart builder pipeline, a constraint engine, and a FAISS+BLaIR retrieval engine — and returns a structured cart with products from a 15,000+ product Amazon catalog.

Your job: write and run a complete Python test suite that stress tests this pipeline end-to-end. Do not mock anything. Hit the real running server. Assert on real responses.

---

## System Architecture (what you're testing)

```
POST /api/mission/build
  └─ LLM goal parser (Groq llama-3.3-70b-versatile)
       └─ domain_router.py → occasion_need_taxonomy.json OR EventAdapter/HomeSetupAdapter
            └─ cart_builder._build_with_needs()
                 ├─ retrieval_engine.retrieve() [FAISS+BLaIR centroid search OR keyword fallback]
                 ├─ catalog scan (15,016 products in catalog.json)
                 ├─ constraint_engine.check_all_constraints() [8 checks per product]
                 ├─ _compute_score() [weighted: need_match, delivery, price_fit, rating, return_risk]
                 └─ quantity_planner.calculate_quantity() [headcount-aware pack sizing]
```

**Catalog facts:**
- 15,000 real Amazon products (McAuley Lab Amazon 2023 dataset, India-focused)
- 16 demo party products appended (B0PARTY*, B0HOME041) for categories Amazon dataset lacks
- FAISS index has 15,000 vectors; new demo products use keyword fallback
- Categories missing from real Amazon data (covered by demo products): balloon_set, balloon_pump, return_gifts, banner, decoration_streamers, tablecloth, trash_bags, party_games, birthday candles (cheap), plain napkins (cheap)

**Scoring weights:**
```
need_match   0.28   (1.0 if product.category in need.category_candidates else 0.3)
delivery     0.22   (1.0 if amazon_now_eligible else 0.4)
now_bonus    0.10   (0.1 if amazon_now_eligible else 0.0)
price_fit    0.18   (max(0, 1 - price / (budget * 0.3)))
rating_norm  0.14   (rating / 5.0)
return_score 0.08   (1.0 - return_risk)
```

**Constraint engine checks (8):**
1. `cost > remaining_budget * 1.1` → fail
2. delivery ETA > deadline_days → fail
3. `not amazon_now_eligible` when deadline ≤ 24h → fail
4. product in incompatible_with list → fail
5. return_risk > threshold (0.30 normal, 0.40 when budget < 500) → fail
6. rating < 3.5 → fail
7. missing safety tag when safety_context set → fail
8. sponsored + any failed check → fail

---

## Test File Structure

Create `tests/test_cart_building_stress.py`. Use `pytest` + `httpx`. The test file must be standalone — no fixtures from conftest. Use `BASE_URL = "http://localhost:8000"`.

---

## Test Suite Requirements

### SECTION 1: Core Happy Path — Birthday Party

These are the most important tests. Every single one must pass.

**Test 1.1 — Coverage: Kids birthday party must achieve 8/8**
```
goal: "Birthday party for 12 kids tomorrow under 4000"
budget_max: 4000
```
Assert:
- `success == True`
- `data.coverage_score.fraction == 1.0`
- `data.coverage_score.covered == 8`
- `data.cart_items` has exactly 8 items
- `data.total_cost <= 4000`
- `data.total_cost > 0`

**Test 1.2 — Product correctness: candles must NOT be decorative holders**
Same goal as 1.1. Find the item where `need_label` contains "Candle" (case-insensitive).
Assert:
- `item.price <= 200` — birthday candles should be cheap (Rs49-99), not Rs1,660 decorative holders
- `item.category in ["candles", "cake_knife"]`
- `item.title` does NOT contain any of: ["holder", "Holder", "stand", "Stand", "décor", "Decor", "Hurricane", "Pillar"]

**Test 1.3 — Product correctness: napkins must be cheap party napkins**
Same goal. Find the item where `need_label` contains "Napkin" or "Tissue" (case-insensitive).
Assert:
- `item.price <= 250` — party napkins should be cheap, not Rs1,080 wedding napkins
- `item.category in ["napkins", "tissue_pack"]`
- `item.title` does NOT contain any of: ["Wedding", "wedding", "Linen", "linen", "Premium Cloth"]

**Test 1.4 — Product correctness: balloons must be actual balloons**
Same goal. Find the item where `need_label` contains "Balloon" (case-insensitive) AND `item.category in ["balloon_set", "balloons", "decorations"]`.
Assert:
- `item.price <= 500` — proper balloon sets, not Rs1,740 cake toppers
- `item.category in ["balloon_set", "balloons"]`
- `item.title` does NOT contain any of: ["Topper", "topper", "Sign", "Garland garland"]

**Test 1.5 — Budget efficiency: meaningful spend with leftover**
Same goal.
Assert:
- `data.total_cost >= 500` — cart is not absurdly cheap (all must-haves filled)
- `data.total_cost <= 3500` — not blowing the whole budget on 8 items
- Remaining budget = 4000 - total_cost > 500 — real room for upgrades

**Test 1.6 — All items are Amazon Now eligible**
Same goal (deadline is "tomorrow" = ≤ 24h). All 8 items must be deliverable.
Assert for each item:
- `item.amazon_now_eligible == True` OR `item.delivery_eta in ["now_20min", "today", "tomorrow"]`

**Test 1.7 — Quantity is sensible for 12 kids**
Same goal. Find the plates item.
Assert:
- `item.packs_quantity >= 1`
- `item.total_cost == item.price * item.packs_quantity`
- Total plates covered = `item.packs_quantity * item.pack_size >= 12` (at least 1 plate per kid)

**Test 1.8 — All items have required fields**
Same goal. For each cart item, assert these fields exist and are non-null:
- `cart_item_id` (string, non-empty)
- `asin` (string, non-empty)
- `title` (string, non-empty)
- `price` (float > 0)
- `total_cost` (float > 0)
- `need_label` (string, non-empty)
- `packs_quantity` (int >= 1)
- `community_adoption_score` (float, 0 < x <= 1.0)
- `sessions_analyzed` (int > 0)
- `constraint_checks_passed` (list, non-empty)

---

### SECTION 2: Budget Edge Cases

**Test 2.1 — Tight budget: must-haves only**
```
goal: "Birthday party for 6 kids today under 800"
budget_max: 800
```
Assert:
- `success == True`
- All selected items have `item.price <= 480` (60% of budget cap for must-have)
- `data.total_cost <= 800`
- Must-have needs covered: plates, cups, candles (at minimum 3 items)
- No item with `price > 400` (no expensive products in tight budget)

**Test 2.2 — Very tight budget triggers partial cart, not failure**
```
goal: "Birthday party for 5 kids under 300"
budget_max: 300
```
Assert:
- `success == True` (MUST be true — partial is OK, failure is not)
- `data.cart_items` has at least 1 item
- `data.total_cost <= 300`
- If `data.coverage_score.fraction < 1.0`: that's acceptable
- The response must NEVER return `success == False` just because budget is tight

**Test 2.3 — Large budget: premium products allowed**
```
goal: "Birthday party for 20 kids this weekend under 15000"
budget_max: 15000
```
Assert:
- `success == True`
- `data.coverage_score.covered >= 6` (at least 6/8 needs covered)
- `data.total_cost <= 15000`
- Premium products may appear (price > 500 is OK here)
- At least one item has `packs_quantity >= 2` (large headcount should trigger multi-pack)

**Test 2.4 — Budget exactly matching cheapest possible cart**
```
goal: "Birthday party for 8 kids tomorrow under 1000"
budget_max: 1000
```
Assert:
- `success == True`
- `data.total_cost <= 1000`
- `data.cart_items` has at least 4 items (must-haves should fit)

---

### SECTION 3: Headcount Scaling

**Test 3.1 — Small party (4 people)**
```
goal: "Birthday party for 4 kids tomorrow under 2000"
budget_max: 2000
headcount: 4
```
Find the plates item. Assert:
- `packs_quantity * pack_size >= 4` (at least 4 plates)
- `packs_quantity * pack_size < 30` (not wildly over-ordering for 4 people)

**Test 3.2 — Large party (50 people)**
```
goal: "Birthday party for 50 people this weekend under 10000"
budget_max: 10000
headcount: 50
```
Find the plates item. Assert:
- `packs_quantity * pack_size >= 50`
- `total_cost <= 10000`

**Test 3.3 — Headcount scales multi-pack correctly**
```
goal: "Office team party for 30 people tomorrow under 5000"
budget_max: 5000
headcount: 30
```
Assert:
- `data.total_cost <= 5000`
- At least one item has `packs_quantity >= 2` (30 people needs multiple packs for consumables)

---

### SECTION 4: Different Occasion Types

**Test 4.1 — Home setup occasion**
```
goal: "New flat setup for 2 people this weekend under 15000"
budget_max: 15000
```
Assert:
- `success == True` OR `data.needs_clarification == True` (clarification is acceptable behavior)
- If success: `data.cart_items` has at least 3 items
- If success: Items should include home categories: mattress OR bedsheet OR pillow OR led_bulb OR extension_board OR towels

**Test 4.2 — Travel occasion**
```
goal: "Trek to Coorg for 4 people this weekend under 5000"
budget_max: 5000
```
Assert:
- `success == True` OR `data.needs_clarification == True`
- If success: `data.cart_items` has at least 2 items
- If success: Items from travel categories: backpack OR water_bottle OR first_aid_kit OR power_bank OR torch

**Test 4.3 — Grocery/essentials**
```
goal: "Weekly groceries for 2 people under 2000"
budget_max: 2000
```
Assert:
- `success == True`
- `data.cart_items` has at least 3 items
- Items from grocery categories: atta OR rice OR dal OR cooking_oil OR detergent OR soap

**Test 4.4 — Diwali celebration**
```
goal: "Diwali decoration for home under 3000"
budget_max: 3000
```
Assert:
- `success == True`
- `data.cart_items` has at least 2 items
- `data.domain` in ["event", "seasonal"] OR the goal parses to a valid domain

---

### SECTION 5: Product Quality Gate — No Bad Products

These tests verify the constraint engine is blocking the right things.

**Test 5.1 — No low-rated products**
```
goal: "Birthday party for 10 kids tomorrow under 4000"
budget_max: 4000
```
For every item in `data.cart_items`, assert:
- `item.rating >= 3.5` (constraint engine check 6 must be working)

**Test 5.2 — No high-return-risk products**
Same goal. For every item:
- `item.return_risk <= 0.30` (constraint engine check 5 must be working)

**Test 5.3 — No out-of-stock products**
Same goal. For every item:
- `item.stock_available == True`

**Test 5.4 — Price-fit: no single item should be > 50% of budget**
Same goal. Budget = 4000. For every item:
- `item.price <= 2000` (pre-filter cap for should_have = 50% of budget)
- If any item.price > 2000 appears, this is a constraint engine bypass bug

**Test 5.5 — Total cost never exceeds budget**
Run 5 different birthday goals with varying budgets:
- 2000, 3000, 4000, 5000, 8000
For each: `data.total_cost <= budget_max`
This must NEVER fail.

---

### SECTION 6: Response Schema Validation

**Test 6.1 — Top-level response shape**
```
goal: "Birthday party for 8 kids under 3000"
budget_max: 3000
```
Assert the following keys exist at `data` level:
- `cart_items` (list)
- `total_cost` (float)
- `coverage_score` (object with `fraction`, `covered`, `total`, `display`, `all_must_haves_covered`, `missing`)
- `domain` (string)
- `occasion` (string)
- `headcount` (int)
- `budget_max` (float)
- `simulated_data` (bool, must be True)

**Test 6.2 — coverage_score consistency**
Same goal. Assert:
- `coverage_score.covered == len(data.cart_items)` — covered count matches actual items
- `coverage_score.fraction == coverage_score.covered / coverage_score.total`
- `0.0 <= coverage_score.fraction <= 1.0`
- `coverage_score.display == f"{coverage_score.covered}/{coverage_score.total}"`

**Test 6.3 — simulated_data flag must always be True**
Same goal. Assert:
- `data.simulated_data == True` — SACRED RULE, must never be False

**Test 6.4 — Each cart item community fields**
Same goal. For each cart_item:
- `0.5 <= item.community_adoption_score <= 1.0`
- `item.sessions_analyzed >= 1000`
- `item.quantity_basis` is a non-empty string
- `item.evidence_source` is a non-empty string

---

### SECTION 7: Occasion Taxonomy Routing

**Test 7.1 — Taxonomy routing: kids_birthday produces balloon_pump need**
```
goal: "Birthday party for 12 kids tomorrow under 4000"
budget_max: 4000
```
Assert:
- At least one item has `need_label` containing "Balloon" (case-insensitive)
- At least one item has `item.category == "balloon_set"` 
  — this verifies FAISS primary-category guarantee is working (B0PARTY013/014 must appear)

**Test 7.2 — Taxonomy routing: need_labels match expected categories**
Same goal. Collect all `item.need_label` values. Assert the following labels appear (case-insensitive substring match):
- "Plate" or "Utensil"
- "Cup" or "Drink"
- "Candle"
- "Balloon" or "Decoration"
- "Napkin" or "Tissue"

**Test 7.3 — Event adapter fallback: generic party goal**
```
goal: "House party for 15 adults next week under 5000"
budget_max: 5000
```
Assert:
- `success == True`
- `data.cart_items` has at least 4 items
- Domain = "event"

---

### SECTION 8: Retrieval Engine Behavior

**Test 8.1 — Demo products appear in results (FAISS out-of-index products)**
```
goal: "Birthday party for 12 kids tomorrow under 4000"
budget_max: 4000
```
The following ASINs were added AFTER the FAISS index was built. They must still appear in results because of the primary-category guarantee:
- `B0PARTY021` (birthday candles, Rs49) OR `B0PARTY022` (Rs69)
- `B0PARTY013` (balloon set, Rs199) OR `B0PARTY014` (Rs249)
- `B0PARTY009` (napkins, Rs79) OR `B0PARTY010` (tissue_pack, Rs59)

Assert: at least 2 of these ASINs appear in `data.cart_items`.

**Test 8.2 — Price fit prefers cheap over expensive in same category**
Look at the candles item from a birthday build. Assert:
- If both B0PARTY021 (Rs49) and any product with price > 500 in category "candles" exist in catalog, the cheap one wins
- `candles_item.price <= 200`

This verifies `price_fit = max(0, 1 - price/(budget*0.3))` is working: Rs49 scores ~0.96 on price_fit, Rs1660 scores 0.0.

**Test 8.3 — Category exclusivity: no two items from same category**
```
goal: "Birthday party for 12 kids tomorrow under 4000"
budget_max: 4000
```
Collect `[item.category for item in data.cart_items]`. Assert:
- `len(categories) == len(set(categories))` — no duplicate categories
- The `used_categories` deduplication in cart_builder must be working

---

### SECTION 9: Concurrent and Repeat Builds

**Test 9.1 — Same goal twice returns consistent coverage**
Call `POST /api/mission/build` twice with the same birthday goal.
Assert:
- Both return `success == True`
- Both return `coverage_score.covered >= 6`
- Both return products in the same 5 categories (plates, cups, candles, balloons, napkins at minimum)
- `abs(response1.total_cost - response2.total_cost) < 500` — cost should be stable

**Test 9.2 — 5 rapid sequential builds don't degrade**
Call build 5 times sequentially with the same goal. Assert:
- All 5 return `success == True`
- All 5 return `coverage_score.covered >= 6`
- No call takes > 10 seconds (measure with time.time())
- Server does not return 500 errors

**Test 9.3 — Different goals don't interfere with each other**
Call 3 different goals back to back:
1. Birthday party for 12 kids under 4000
2. Trek to Coorg for 4 people under 3000
3. Birthday party for 8 kids under 2500

Assert each response has the correct domain:
- Goal 1: `domain == "event"`
- Goal 2: `domain in ["travel", "travel_prep"]`
- Goal 3: `domain == "event"`

And no response contains items from the wrong domain (no trekking gear in birthday cart).

---

### SECTION 10: Error Handling and Boundary Cases

**Test 10.1 — Completely unachievable goal returns graceful response**
```
goal: "Buy a Ferrari under 100"
budget_max: 100
```
Assert:
- Does NOT return a 500 error
- Either `success == True` with some partial cart, OR `success == False` with `needs_clarification == True` or `unsupported == True`
- Response time < 10 seconds

**Test 10.2 — Empty goal doesn't crash server**
```
goal: ""
budget_max: 1000
```
Assert:
- Does NOT return a 500 error (status code must be 200 or 422, not 500)

**Test 10.3 — Missing budget uses default**
```
goal: "Birthday party for 10 kids tomorrow"
(no budget_max field)
```
Assert:
- Does NOT return a 500 error
- `success == True` or `needs_clarification == True`
- If success: some cart items returned

**Test 10.4 — Very large headcount doesn't crash**
```
goal: "Birthday party for 500 kids tomorrow under 50000"
budget_max: 50000
headcount: 500
```
Assert:
- Does NOT return a 500 error
- `success == True` or `needs_clarification == True`
- If success: `data.total_cost <= 50000`

**Test 10.5 — Budget_max = 0 is handled gracefully**
```
goal: "Birthday party for 5 kids tomorrow"
budget_max: 0
```
Assert:
- Does NOT crash (no 500 error)

---

### SECTION 11: Specific Product Category Checks

Run `goal: "Birthday party for 12 kids tomorrow under 4000", budget_max: 4000` once and reuse the response for all these checks.

**Test 11.1 — Plates item sanity**
- `category in ["plates", "disposable_plates"]`
- `price >= 40` and `price <= 500`
- `pack_size >= 10` (plates come in packs, not singles)

**Test 11.2 — Cups item sanity**
- `category in ["cups", "disposable_cups"]`
- `price >= 40` and `price <= 400`
- `pack_size >= 10`

**Test 11.3 — Candles item sanity**
- `category in ["candles", "cake_knife"]`
- `price >= 30` and `price <= 200` (birthday candles are cheap)
- `pack_size >= 1`

**Test 11.4 — Balloon item sanity**
- `category in ["balloon_set", "balloons"]` (NOT "decorations")
- `price >= 100` and `price <= 600`
- `pack_size >= 20` (balloon sets come in bulk)

**Test 11.5 — Napkins/tissue item sanity**
- `category in ["napkins", "tissue_pack"]`
- `price >= 30` and `price <= 300`

---

### SECTION 12: Performance Benchmarks

**Test 12.1 — Response time under 15 seconds**
Measure wall time for `POST /api/mission/build` with birthday goal.
Assert: `elapsed_seconds < 15`

Note: First call may hit LLM (Groq ~600ms). Repeat calls use cache. Test the first call.

**Test 12.2 — Health endpoint always 200**
Assert `GET /health` returns `status_code == 200`.
This is a sacred rule — health must always return 200.

**Test 12.3 — Coverage doesn't degrade with large catalog**
The catalog has 15,016 products. Assert that birthday party build still achieves >= 7/8 coverage.
(Regression: if catalog grows and wrong products start scoring higher, coverage drops.)

---

## Implementation Notes for Codex

1. **Use `httpx.Client` (sync)**, not `requests`, for cleaner timeout handling.
2. **One session-level fixture** does the birthday build once and shares the response across tests in Section 11 — don't rebuild for every assertion.
3. **Parametrize Section 5.5** over 5 budget values.
4. **Mark slow tests** with `@pytest.mark.slow` — tests in Section 9 (repeat builds) are slow.
5. **All assertions must have descriptive messages** — `assert x, f"Expected x but got {actual}"`.
6. **Do not mock the LLM** — hit the real Groq endpoint. Tests will have realistic timing.
7. **For tests that accept both `success==True` and `needs_clarification==True` (home setup, tight budget)** — check `response.get("success")` and `response.get("data", {}).get("needs_clarification")` separately.
8. **Print the full response JSON** on assertion failure so debugging is easy.

## Running the Tests

```bash
# All tests
pytest tests/test_cart_building_stress.py -v

# Only fast tests (skip slow section 9)
pytest tests/test_cart_building_stress.py -v -m "not slow"

# Only the critical Section 1 (happy path)
pytest tests/test_cart_building_stress.py -v -k "test_1_"

# With coverage report
pytest tests/test_cart_building_stress.py -v --tb=short 2>&1 | tee test_results.txt
```

## Expected Results

| Section | Tests | Expected Pass Rate |
|---------|-------|-------------------|
| 1. Happy Path | 8 tests | 8/8 (100%) — these are blocking |
| 2. Budget Edge Cases | 4 tests | 4/4 |
| 3. Headcount Scaling | 3 tests | 3/3 |
| 4. Occasion Types | 4 tests | 3/4 (home setup may clarify) |
| 5. Product Quality Gate | 5 tests | 5/5 |
| 6. Schema Validation | 4 tests | 4/4 |
| 7. Taxonomy Routing | 3 tests | 3/3 |
| 8. Retrieval Engine | 3 tests | 3/3 |
| 9. Concurrent Builds | 3 tests | 3/3 |
| 10. Error Handling | 5 tests | 5/5 |
| 11. Category Checks | 5 tests | 5/5 |
| 12. Performance | 3 tests | 3/3 |
| **Total** | **50 tests** | **49-50/50** |

## Known Acceptable Failures

- **Test 4.1 (home setup)**: LLM may ask for clarification — `needs_clarification: True` is correct behavior, not a bug.
- **Test 2.2 (Rs300 budget)**: May return 1-3 items with partial coverage — correct.
- **Test 10.2 (empty goal)**: 422 validation error is acceptable — it means FastAPI caught it before it reached the LLM.

## What Counts as a Bug

| Symptom | Root Cause to Investigate |
|---------|--------------------------|
| Candles item price > Rs200 | FAISS returning wrong products; B0PARTY021/022 not in candidates |
| Balloons item is a "topper" or "sign" | primary_exact fix in cart_builder not working |
| Coverage < 6/8 for birthday Rs4000 | Demo products missing from catalog or catalog_embedded.json out of sync |
| Any item.rating < 3.5 | Constraint engine check 6 bypassed |
| Any item.price > budget * 0.50 | Pre-filter cap not applied for should_have needs |
| Two items with same category | used_categories dedup broken in cart_builder |
| total_cost > budget_max | Affordability check bypassed |
| simulated_data == False | SACRED RULE violation — must always be True |
