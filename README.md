# MissionCart — Amazon Now Occasion Operating System

> **Amazon HackOn 2026 | PS3: Reimagine Shopping Experience**

**One-line pitch:** Amazon Now already delivers in minutes. MissionCart makes sure you ordered the right things.

---

## 🎯 Problem Statement

Amazon Now delivers in 10–20 minutes. But customers still spend 8–15 minutes **deciding** what to order — searching product by product, guessing quantities, missing accessories, and discovering incompatibilities only after delivery. For goal-driven occasions (parties, home setup, travel prep), this friction is the highest. MissionCart eliminates the decision work entirely.

---

## 💡 Solution

MissionCart is an **occasion operating system** built on top of Amazon Now. It understands WHY you need something, builds the complete basket automatically, catches every error before checkout, and ensures the cart is **correct by construction** — not by suggestion.

---

## ✨ Core Features

### Tier 1: Fully Functional (Live Demo)

| # | Feature | What It Does |
|---|---------|--------------|
| 1 | **Goal-Based Cart Building** | Type "Birthday party for 12 kids tomorrow under ₹4000" → complete validated cart in 3 seconds |
| 2 | **Cart Audit (4 Flags)** | Catches wrong quantities, missing accessories, delivery failures, and sponsored trust violations — all animated in sequence |
| 3 | **Morning Grocery Approval** | One-tap reorder of predicted daily essentials via Amazon Now. Depletion alerts computed from purchase history |
| 4 | **AI Comparison Engine** | Detects indecision (switching between products 3× in 60s) → auto-surfaces goal-aware deterministic comparison with Groq explanation |
| 5 | **Occasion Intelligence Feed** | Proactive cards for upcoming occasions with recurrence from past missions |
| 6 | **Amazon Quorum (Group Cart)** | Collaborative shopping with voting, budget optimizer, and proportional payment split |
| 7 | **Product Search with Badges** | FAISS semantic retrieval + badge engine (best value, most popular, top rated, instant delivery, trusted brand) |
| 8 | **Pre-Checkout Intelligence** | 5 checks before payment: late items, price drops, compatibility gaps, quantity risk, budget insight |

### Tier 2: Beautiful Static Screens

| Feature | Description |
|---------|-------------|
| Community Goal Pages | "What 3,847 birthday planners bought" — zero sponsored products |
| User Identity Groups | "Office Gym Dad", "JEE Prep Student" — psychographic product sections |
| Seller Demand Intelligence | Demand forecasts for sellers by occasion type and city |
| Mission Share Cards | Shareable "Riya's Birthday — 9 items, ₹3,850" cards |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Native App (Expo SDK 51)            │
│  Home · Search · Audit · Cart · Quorum · Reorder · Discover │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend (Python 3.11)              │
├─────────────────────────────────────────────────────────────┤
│  Mission Parser ──────── Domain Router ──── Cart Builder    │
│  (Groq LLM)              EventAdapter      Quantity Planner │
│                           HomeAdapter       Constraint Eng.  │
│                           TravelAdapter     Budget Repair    │
│                                             Compatibility    │
├─────────────────────────────────────────────────────────────┤
│  Retrieval Engine ─── BLaIR FAISS (234 products, dim=1024)  │
│  Badge Engine ──────── Community Priors (simulated)          │
│  Comparison Engine ─── 7-phase deterministic scoring         │
│  Audit Engine ────────  5-check constraint validation        │
│  Hive Engine ─────────  Group optimizer + payment split      │
├─────────────────────────────────────────────────────────────┤
│  LLM Providers: Groq │ Anthropic │ Bedrock │ Gemini         │
│  Prompt Cache: 2-level (memory TTL + disk persistent)        │
│  Data: catalog.json (241 SKUs) + simulated/ (50 users)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔬 Technical Depth

### 14-Step Cart Building Pipeline

```
Goal Input → LLM Parse → Domain Route → Need Decompose → Quantity Plan
→ Catalog Retrieve (FAISS) → Constraint Check (5 rules) → Score & Rank
→ Sponsored Filter → Budget Repair → Compatibility Pass → Coverage Score
→ Community Enrichment → Response
```

### Comparison Engine (7 Phases)

```
Classify Mission → Hard Constraints (6 rules) → Deterministic Score
→ Community Evidence [0.95–1.05] → Winner + Confidence → LLM Explain
→ Audit Trace
```

### Key Algorithms

| Algorithm | Complexity | Description |
|-----------|-----------|-------------|
| MissionFitScore | O(N×C) | Weighted: delivery(0.30) + price(0.30) + quantity(0.25) + quality(0.15) |
| Quantity Planner | O(1) | `ceil(headcount × usage_rate × buffer ÷ pack_size)` |
| Budget Repair | O(N) | 5-step: trim buffer → swap cheaper → drop optional → drop should_have → never drop must_have |
| Switching Detection | O(1) | Sliding window of 6 views, 2 unique ASINs, same category, 60s window |
| Hive Optimizer | O(N) | 3 rules: remove low-voted → swap family packs → deduplicate ASINs |

### Constraint Engine (5 Checks)

1. **Budget** — cost ≤ remaining × 1.1
2. **Delivery** — ETA ≤ deadline days
3. **Amazon Now** — if deadline ≤ 24h, must be Now-eligible
4. **Safety** — child_safe/baby_safe/pet_safe tag required
5. **Sponsored** — blocked if fails any other check (trust gate)

---

## 📊 Real vs Mock Disclosure

| Component | Status | Details |
|-----------|--------|---------|
| Mission Parser (LLM) | **REAL** | Groq llama-3.1-8b-instant with prompt caching |
| Constraint Engine | **REAL** | 5 checks running on every product |
| Quantity Arithmetic | **REAL** | Formula-based from quantity_rules.json |
| Budget Repair | **REAL** | 5-step deterministic sequence |
| Compatibility Graph | **REAL** | 28 category edges, auto-adds missing accessories |
| FAISS Retrieval | **REAL** | 234 vectors, dim=1024, <3ms latency |
| Comparison Engine | **REAL** | 7-phase deterministic scoring + Groq explanation |
| Badge Engine | **REAL** | 241 badges computed at startup from 7-rule waterfall |
| Amazon Cart URL | **REAL** | Opens amazon.in with items pre-loaded |
| Product Catalog | **MOCK** | 241 curated SKUs with realistic Indian pricing |
| Purchase History | **MOCK** | 50 simulated users, 452 orders for U001 |
| Community Sessions | **MOCK** | Simulated occasion data (disclosed as simulation-based) |
| Depletion Alerts | **MOCK** | Computed from simulated purchase intervals |
| Identity Groups | **MOCK** | Static screens with hardcoded profiles |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Android device with USB debugging OR Android emulator

### One-Command Launch (Windows)

```bash
cd missioncart
launch.bat
```

### Manual Launch

**Terminal 1 — Backend:**
```bash
cd missioncart/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd missioncart/frontend
npm install
npx expo start --android
```

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and set at least one LLM key:

```env
GROQ_API_KEY=your_groq_key_here          # Recommended (free, fast)
# ANTHROPIC_API_KEY=your_key             # Alternative
# GEMINI_API_KEY=your_key                # Alternative
# LLM_PROVIDER=groq                      # Force specific provider
```

System auto-detects the first available key. Falls back to regex parser if none set.

---

## 📡 API Endpoints

### Mission Building
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/mission/parse` | Parse goal → MissionSpec |
| POST | `/api/mission/build` | Full pipeline → validated cart |
| POST | `/api/mission/audit` | Audit existing cart → flags + repair |

### Search & Comparison
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search/products?q=&occasion=` | Search with badges |
| GET | `/api/search/suggest?q=` | Autocomplete |
| POST | `/api/comparison/evaluate` | 7-phase deterministic comparison |
| POST | `/api/comparison/compare` | Quick comparison (legacy) |

### Reorder & Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reorder/draft` | Today's reorder with confidence scores |
| POST | `/api/reorder/approve` | Idempotent order placement |
| POST | `/api/intelligence/pre-checkout` | 5 pre-checkout warnings |

### Amazon Quorum (Group Cart)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/quorum/demo` | Pre-seeded group cart demo |
| POST | `/api/quorum/cart/{id}/add-item` | Add product (JSON body) |
| POST | `/api/quorum/cart/{id}/vote` | Upvote/downvote item |
| POST | `/api/quorum/cart/{id}/optimize` | Rule-based budget optimizer |
| GET | `/api/quorum/cart/{id}/split` | Equal or proportional split |
| POST | `/api/quorum/messages/send` | Send chat message |
| POST | `/api/quorum/hive/{id}/budget` | Update budget cap |

### Demo & Presentation
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/demo/scenarios` | Sneha's broken cart (audit demo) |
| GET | `/api/demo/occasions` | 4 occasion cards with recurrence |
| GET | `/api/demo/reorder-alerts` | Urgent depletion alerts |
| GET | `/api/demo/user-profile` | U001 stats from simulated data |
| GET | `/api/demo/voice-input-example` | Hinglish voice parse demo |
| GET | `/api/demo/seller-insights` | Seller demand intelligence |
| GET | `/api/demo/mission-share-card` | Shareable mission summary |
| GET | `/api/demo/notification-content` | Push notification content |
| POST | `/api/demo/warm` | Pre-warm caches for demo |
| GET | `/api/demo/cache-stats` | LLM cache hit rates |

---

## 🎬 Demo Script (3 Minutes)

| Time | Action | What Judges See |
|------|--------|-----------------|
| 0:00 | Morning approval card | One-tap reorder → haptic → "Ordered ✓" |
| 0:20 | Occasion card: Riya's birthday | Tap → audit flow begins |
| 0:40 | **Audit: 4 flags animate** | Flag 1: "12 plates, you need 24" (red) |
| 1:00 | Flag 2 | "Balloon set — no pump" (red) |
| 1:10 | Flag 3 | "Streamers not on Amazon Now" (amber) |
| 1:20 | **Flag 4** | "Sponsored cups blocked — child_safe" (**blue** trust moment) |
| 1:30 | Fix All → repair animation | Budget ₹4,340 → ₹3,850, Coverage 9/9 |
| 1:50 | Comparison popup | Switch between products 3× → AI comparison slides up |
| 2:10 | Goal build | Type "Birthday party for 12 kids" → 8 items in 3s |
| 2:30 | Architecture slide | "LLM plans. Solver verifies. Cart correct by construction." |
| 3:00 | Close | "Amazon Now delivers in minutes. MissionCart makes sure you ordered the right things." |

---

## 📈 Scalability Story

| Component | Hackathon | Production (Amazon) |
|-----------|-----------|---------------------|
| Backend | FastAPI + Railway | AWS ECS + API Gateway |
| Database | JSON files | Amazon Aurora + DynamoDB |
| LLM | Groq (free tier) | Amazon Bedrock (reserved) |
| Graph | JSON compatibility | Amazon Neptune |
| Retrieval | FAISS (234 vectors) | FAISS + SageMaker (millions) |
| Notifications | Expo local | AWS SNS + FCM |
| User Profiling | Mock groups | Amazon Personalize |
| Search | In-memory filter | Amazon OpenSearch |

**Scale numbers:** 600K daily sessions × 10 min saved = 100K customer-hours/day recovered

---

## 🏆 What Makes This Novel

1. **Identity Groups over Item Groups** — First e-commerce platform organized around WHO you are, not what you searched
2. **Cart Audit before Checkout** — Nobody catches cart errors before payment. We do.
3. **Behavior-Detected Comparison** — No platform detects switching and auto-surfaces goal-aware comparison
4. **Deterministic + Explainable** — LLM plans, solver verifies. Every recommendation is traceable through score audit
5. **Amazon Now Integration** — Every feature filters for instant delivery eligibility first

---

## 👥 Team

| Name | Role | Contribution |
|------|------|-------------|
| Anmol Jain | Full Stack + PM | Architecture, Backend, AI Integration |

---

## 📁 Project Structure

```
missioncart/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan warmup
│   │   ├── routers/                   # 8 route modules
│   │   │   ├── mission.py             # parse, build, audit
│   │   │   ├── search.py              # products, badges, suggest
│   │   │   ├── comparison.py          # evaluate, compare
│   │   │   ├── hive.py                # quorum group cart
│   │   │   ├── reorder.py             # morning cart + approve
│   │   │   ├── intelligence.py        # pre-checkout checks
│   │   │   ├── demo.py                # 10+ demo endpoints
│   │   │   └── catalog.py             # product catalog
│   │   ├── services/
│   │   │   ├── mission_parser.py      # Groq LLM + regex fallback
│   │   │   ├── cart_builder.py        # Full pipeline orchestrator
│   │   │   ├── domain_router.py       # EventAdapter, HomeAdapter, TravelAdapter
│   │   │   ├── quantity_planner.py    # Formula-based quantity math
│   │   │   ├── constraint_engine.py   # 5-check validation
│   │   │   ├── budget_repair.py       # 5-step repair sequence
│   │   │   ├── compatibility.py       # Accessory graph
│   │   │   ├── retrieval_engine.py    # BLaIR FAISS + community enrichment
│   │   │   ├── audit_engine.py        # Real-time cart audit
│   │   │   ├── badge_engine.py        # 7-rule badge waterfall
│   │   │   ├── hive_engine.py         # Group optimizer + split
│   │   │   ├── comparison/            # 7-phase comparison engine
│   │   │   └── llm/                   # Multi-provider + cache
│   │   ├── models/                    # Pydantic schemas
│   │   └── data/                      # Catalog + simulated data
│   ├── Dockerfile                     # Railway deployment
│   ├── requirements.txt
│   └── test_demo.py                   # 15-point regression suite
├── frontend/
│   ├── src/
│   │   ├── app/                       # Expo Router screens
│   │   │   ├── (tabs)/               # Home, Missions, Discover, Profile
│   │   │   ├── audit.tsx              # 4-flag animation sequence
│   │   │   ├── cart/                  # Building + Result screens
│   │   │   ├── search.tsx             # FAISS search + badges
│   │   │   └── hive/                  # Quorum group cart
│   │   ├── components/                # Reusable UI
│   │   ├── lib/                       # API client, types, constants
│   │   └── store/                     # Zustand state
│   └── package.json
├── scripts/                           # Launch helpers
│   ├── launch.bat / launch.sh         # One-command start
│   ├── update_env.py                  # Auto-detect LAN IP
│   └── health_check.py               # Backend readiness check
└── README.md                          # This file
```

---

## 🧪 Testing

```bash
cd missioncart/backend
python test_demo.py
```

Expected output:
```
MISSIONCART DEMO READINESS TEST
  ✓ Health: PASS
  ✓ Parse - domain: PASS
  ✓ Parse - headcount: PASS
  ✓ Parse - safety: PASS
  ✓ Build - success: PASS
  ✓ Build - items: PASS
  ✓ Build - no sponsored: PASS
  ✓ Build - community fields: PASS
  ✓ Build - under 3s: PASS
  ✓ Audit - 4 flags: PASS
  ✓ Audit - flag4 blue: PASS
  ✓ Audit - repaired total: PASS
  ✓ Occasions: PASS
  ✓ Reorder alerts: PASS
  ✓ Home setup - no party items: PASS
  15/15 tests passing
  Demo confidence: 100%
  STATUS: DEMO READY
```

---

## 📜 License

Built for Amazon HackOn 2026. For jury evaluation only.

---

> *"Start with the customer. Work backwards. From need to done."*
