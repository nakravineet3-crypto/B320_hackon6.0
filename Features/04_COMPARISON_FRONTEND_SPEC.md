# Feature: Smart Comparison — Frontend Implementation Spec
## For: Vineet (Frontend)
## Backend owner: Anmol

---

## What changed on the backend

The `/evaluate` comparison endpoint now returns a `decision_type` field and
a new response shape. **The frontend must not use the old `/compare` endpoint
for the comparison screen** — use `/evaluate` only.

---

## API Endpoint

```
POST /compare/evaluate
```

### Request body

```json
{
  "product_a": { ...product object... },
  "product_b": { ...product object... },
  "mission_spec": {
    "headcount": 4,
    "budget_max": 500,
    "occasion_type": "general",
    "deadline_hours": 48
  },
  "user_id": "U001"
}
```

`user_id` must be passed from the logged-in user's session.
Demo users available: `"DEMO_BUDGET"`, `"DEMO_PREMIUM"`, `"U001"`–`"U005"`.

---

## Response shape (what the frontend receives)

```json
{
  "success": true,
  "data": {
    "decision_type": "winner_selected | substitution_suggested | comparison_suppressed",
    "winner": "a | b | null",
    "confidence": "clear_winner | slight_edge | strong | null",
    "headline": "Maggi Masala Noodles is the better pick",
    "reason": "lower unit cost (matches value-pack preference)",
    "safe_personalization_reason": "Based on your usual value-pack preference.",
    "dominant_factor": "price_per_unit",
    "explanation": "Maggi Masala wins because ₹17/unit beats ₹18/unit...",
    "explanation_source": "groq | groq_cached | template | system",
    "comparison_rows": [
      { "label": "Price per unit", "a_value": "₹17.00/unit", "b_value": "₹18.00/unit", "winner": "a" },
      { "label": "Mission total cost", "a_value": "₹68 for 1 pack(s)", "b_value": "₹72 for 1 pack(s)", "winner": "a" },
      { "label": "Delivery", "a_value": "⚡ 20 min", "b_value": "⚡ 20 min", "winner": "tie" },
      { "label": "Quality", "a_value": "4.1★ · 52,000 reviews", "b_value": "4.3★ · 18,000 reviews", "winner": "b" }
    ],
    "score_a": { "mission_fit_score": 0.73, "price_per_unit": 17.0, "price_per_unit_score": 1.0, ... },
    "score_b": { "mission_fit_score": 0.69, "price_per_unit": 18.0, "price_per_unit_score": 0.944, ... },
    "substitute": null,
    "eliminations": [],
    "weights_used": { "price_per_unit": 0.39, "quantity": 0.25, "delivery": 0.24, "quality": 0.12 },
    "audit_trace_id": "uuid",
    "simulated_data": true
  }
}
```

---

## Screen layout

The comparison screen has 4 zones from top to bottom:

```
┌──────────────────────────────────────────────────┐
│  ZONE 1: VERDICT HEADER                          │
│  Large text: data.headline                       │
│  Small text: data.safe_personalization_reason    │
│  Confidence badge: data.confidence               │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  ZONE 2: PRODUCT CARDS                           │
│  Left: Product A (winner highlighted if a)       │
│  Right: Product B (winner highlighted if b)      │
│  Winner gets: colored border, "PICK THIS" badge  │
│  Loser gets: 50% opacity, no badge               │
│  BOTH get: image, title, price                   │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  ZONE 3: COMPARISON TABLE                        │
│  Renders data.comparison_rows as rows            │
│  Each row: label | A value | B value             │
│  Winner cell highlighted per row.winner          │
│  "tie" = both cells normal, no highlight         │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  ZONE 4: EXPLANATION + CTA                       │
│  data.explanation in a card                      │
│  Primary button: "Add [winner name] to Cart"     │
│  Secondary button: "See all options"             │
└──────────────────────────────────────────────────┘
```

---

## decision_type handling — CRITICAL

The frontend must branch on `data.decision_type`. Never assume winner is always set.

### `winner_selected` (normal case)
- Render all 4 zones as described above.
- `data.winner` is `"a"` or `"b"`.
- Highlight the winning product card.

### `substitution_suggested`
- Zone 1: Show "Neither is ideal for this goal"
- Zone 2: Show both product cards at 50% opacity, no winner badge
- Zone 3: Show comparison table normally (still useful)
- Zone 4: Show message from `data.substitute.reason` + "Browse better options" button
- Do NOT show "Add to cart" for either product.

### `comparison_suppressed`
- Zone 1: Show `data.headline` (already set to "Neither product meets the requirements")
- Zones 2-3: Dimmed, no winner
- Zone 4: Show `data.explanation` + "Try different products" button

---

## Confidence badge display

| confidence value | Badge text | Badge color |
|---|---|---|
| `clear_winner` | "Clear Pick" | Green |
| `slight_edge` | "Slight Edge" | Blue |
| `strong` | "Clear Pick" | Green |
| `null` | (no badge) | — |

---

## Personalization line

Display `data.safe_personalization_reason` in small italic text below the headline.

```
Example: "Based on your usual value-pack preference."
```

This line MUST be the `safe_personalization_reason` field — NOT `dominant_factor`,
NOT any cohort label.

**Never display:** "You are a Budget Essentials Buyer" or any cohort name.

---

## Comparison row rendering

Each row in `data.comparison_rows`:

```
{ "label": "Price per unit", "a_value": "₹17.00/unit", "b_value": "₹18.00/unit", "winner": "a" }
```

Render as a 3-column row:
- Column 1: label (grey text)
- Column 2: a_value (highlight if winner == "a")
- Column 3: b_value (highlight if winner == "b")
- If winner == "tie": both columns have equal styling

Use a green checkmark icon on the winning cell.

---

## Simulated data banner

When `data.simulated_data == true`, show a small banner:

```
"⚡ Simulated data for demo"
```

Small text, placed at the very bottom of the screen, not in the main flow.

---

## What NOT to build

- Do NOT show a "which matters more to you?" selector before the comparison.
  The backend handles this automatically. No pre-comparison preference screen.

- Do NOT show "too close to call" or "it depends" states.
  Every `winner_selected` response has a decisive winner.
  If scores are very close, the backend tiebreaker already resolved it.

- Do NOT display `data.weights_used` to the user. It's for the audit trace only.

- Do NOT display `data.score_a.mission_fit_score` raw numbers.
  Use comparison_rows for user-visible data only.

---

## Demo flow to test

1. Navigate to the comparison screen with user_id = "DEMO_BUDGET"
2. Compare Maggi Masala 4-pack (₹68) vs Maggi Atta 4-pack (₹72)
3. Expected result: Masala wins, "Based on your usual value-pack preference."

4. Switch user_id to "DEMO_PREMIUM" (can be a toggle in dev mode)
5. Same comparison
6. Expected result: Atta wins, "Based on your preference for higher-rated products."

That is the demo moment. Same screen, same two products, different users, different winners.

---

## Navigation into comparison screen

The comparison screen is triggered when the user long-presses or taps a "Compare"
button on a product card. It receives two product objects + the current mission spec.

If the screen is entered from a cart-building mission, pass the mission spec
(headcount, budget_max, deadline_hours) from the active mission context.
