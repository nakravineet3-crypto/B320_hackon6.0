# MissionCart
### Amazon HackOn 2026 | PS3: Reimagine Shopping Experience

> **"Amazon Now delivers in minutes. MissionCart makes sure you ordered the right things."**

---

## The Problem

When customers have a goal — not a product — Amazon forces them to decompose it manually. Planning a birthday party for 12 kids means 15-20 individual searches, quantity guesses, and missing accessories discovered only after delivery.

**MissionCart eliminates the decision work entirely.**

---

## Five Features

| Feature | What it does |
|---|---|
| **Morning Approval** | 7AM notification with routine reorder. One tap = ordered. |
| **Goal Builder** | Type a goal → get a complete, validated cart with correct quantities |
| **Cart Audit** | Show any cart → system finds every error before checkout |
| **AI Comparison** | Switch between 2 products 3x → comparison popup auto-appears |
| **Occasion Feed** | Diwali in 24 days → tap to plan the complete occasion |

---

## Novel Claim

**Identity groups connect PEOPLE to products, not products to products.**

Amazon organizes by item type. MissionCart organizes by who you are. Office Gym Dad sees different products than JEE Student — not because of purchase history, but because of community-validated occasion data.

---

## Architecture

```
Natural Language Goal
        ↓
[LLM — intent parsing only]
Claude Haiku via Groq/Bedrock/Anthropic (modular)
        ↓
Mission Spec JSON
{domain, headcount, deadline_hours, budget_max, safety_context}
        ↓
Domain Adapter (EventAdapter / HomeSetupAdapter / TravelAdapter)
Decomposes goal into prioritized needs
        ↓
Quantity Planner
ceil(headcount × usage_rate × buffer) ÷ pack_size
        ↓
BLaIR Retrieval + FAISS
Semantic product search (pretrained on Amazon Reviews 2023)
        ↓
Constraint Solver (8 checks)
budget / delivery / Amazon Now / compatibility / return_risk / quality / safety / sponsored validity
        ↓
Budget Repair (if over budget)
Drop optional → swap cheaper → never drop must-have
        ↓
[LLM — explanation only]
Translates evidence numbers into natural language
        ↓
Validated cart with community evidence
```

---

## Real vs Mock

| Component | Status | Details |
|---|---|---|
| LLM goal parsing | **REAL** | Groq/Anthropic/Bedrock — modular provider |
| Quantity calculation | **REAL** | Formula: headcount × usage_rate × buffer ÷ pack_size |
| Constraint solver | **REAL** | 8 checks per product, deterministic |
| Budget repair | **REAL** | Greedy drop with priority ordering |
| Coverage score | **REAL** | Computed from needs vs cart |
| BLaIR retrieval | **REAL** | hyp1231/blair-roberta-large + FAISS |
| Community adoption % | **DEMO PRIOR** | Informed estimates; production would compute from purchase sessions |
| Product catalog | **MOCK** | 234 curated SKUs with realistic Indian pricing |
| Purchase history | **MOCK** | 3 hardcoded reorder alerts |
| Amazon Now inventory | **MOCK** | Static eligibility flags per SKU |
| Community pages | **MOCK** | Static screen |

---

## Tech Stack

**Backend:** Python 3.11, FastAPI 0.111.0, Pydantic v2
**Frontend:** React Native 0.74, Expo SDK 51, Reanimated 3.10
**LLM:** Modular — Groq (Llama 3.1) / Anthropic Claude / Amazon Bedrock / Gemini
**Retrieval:** BLaIR + FAISS (semantic product search)
**Deploy:** Railway (backend), Expo Go (demo)

---

## Run Locally

**Backend:**
```bash
cd missioncart/backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
# Create .env with GROQ_API_KEY=your_key
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd missioncart/frontend
npx expo start --android
```

**Verify:**
```bash
curl http://localhost:8000/health
# → {"status": "ok", "service": "missioncart-backend"}
```

---

## Production Scale

| Component | Hackathon | Production |
|---|---|---|
| Backend | FastAPI on Railway | AWS ECS auto-scaling |
| Database | SQLite | Amazon Aurora Serverless |
| LLM | Groq/Anthropic | Amazon Bedrock |
| Product graph | FAISS flat index | Amazon Neptune |
| Notifications | Local (Expo) | AWS SNS + FCM |
| Community data | Demo priors | Amazon Personalize |

**Impact numbers:**
- Amazon Now: ~3M orders/day in India
- Goal-driven occasions: ~20% = 600K sessions/day
- Time saved: 8 min → 45 sec per session
- = 1.2M customer-hours returned daily

---

## Demo Script (3 minutes)

1. **(0:00)** Morning approval card → Tap "Approve & Order" → haptic
2. **(0:20)** Tap "Try Cart Audit" → 4 flags animate in sequence
   - Flag 4 is BLUE (not red) — sponsored blocked = trust moment
3. **(1:30)** Missions tab → "Birthday Party" chip → 4-step build
4. **(2:10)** "Demo: Show AI comparison" → bottom sheet slides up
5. **(2:30)** Discover tab → Office Gym Dad → "No sponsored products"
6. **(2:50)** "Add to Amazon Cart" → amazon.in opens

---

*Built for Amazon HackOn 2026 in 48 hours.*
*Team: [Your name]*
