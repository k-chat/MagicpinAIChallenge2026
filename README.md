# Vera AI Bot — Merchant Growth Assistant

A high-scoring AI chatbot that composes personalized WhatsApp messages for merchant growth using a 4-context framework.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Bot
```bash
python bot.py
```

The bot will start on `http://localhost:8080`.

### 3. Verify Health
```bash
curl http://localhost:8080/healthz
```

## Architecture

### 5 HTTP Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Health check |
| `/metadata` | GET | Bot capabilities & version |
| `/v1/context` | POST | Receive context (idempotent by version) |
| `/v1/tick` | POST | Periodic wake-up to compose messages |
| `/v1/state` | GET | Debug: current loaded contexts |

### 4-Context Composition Framework

Every message is composed from these contexts:

```
┌──────────────────────────┐
│   CategoryContext        │ ← Slow, shared across vertical
│ (voice, offers, digest)  │   (dentists, salons, etc.)
└──────────────────────────┘
         ↓
┌──────────────────────────┐
│   MerchantContext        │ ← Per-business state
│ (perf, offers, history)  │   (daily + real-time)
└──────────────────────────┘
         ↓
┌──────────────────────────┐
│   TriggerContext         │ ← Event-driven
│ (research_digest, etc.)  │   (why NOW?)
└──────────────────────────┘
         ↓
┌──────────────────────────┐
│   CustomerContext (opt)  │ ← For customer-facing
│ (relationship, consent)  │   (optional)
└──────────────────────────┘
         ↓
    Composer.compose()
         ↓
┌──────────────────────────┐
│   ComposeResponse        │
│ {body, cta, send_as,    │
│  suppression_key,        │
│  rationale}              │
└──────────────────────────┘
```

## Scoring Rubric (Judge Evaluates)

Your messages are scored 0-10 on each dimension:

### 1. **Decision Quality** (/10)
- Pick ONE signal that should drive this message
- Don't repeat every available fact
- Combine trigger + merchant state + category fit

### 2. **Specificity** (/10)
- Use real numbers, offers, dates, local facts
- Ground every claim in the input
- No invented context

### 3. **Category Fit** (/10)
- Match tone to business type
- Honor legal taboos (dentists: no "cure" or "guaranteed")
- Respect seasonal beats and peer norms

### 4. **Merchant Fit** (/10)
- Personalize to metrics (calls, CTR, lapsed customers)
- Reference active offers, conversation history
- Show you know THIS merchant

### 5. **Engagement Compulsion** (/10)
- ONE clear reason to reply NOW
- Low-friction ask with single next action
- Bold hook from real context (not hype)

## Data Model

### CategoryContext
```python
{
  "slug": "dentists",
  "offer_catalog": ["Dental Cleaning @ ₹299", "Free Consultation"],
  "voice": {
    "tone": "clinical",
    "taboo_terms": ["cure", "guaranteed"],
    "allowed_terms": ["fluoride varnish", "3-month recall"]
  },
  "peer_stats": {
    "avg_rating": 4.4,
    "avg_reviews": 62,
    "avg_ctr": 0.030
  },
  "digest": [...],  # Weekly research items (source-cited)
  "seasonal_beats": [...],
  "trend_signals": [...]
}
```

### MerchantContext
```python
{
  "merchant_id": "m_001_drmeera_dentist_delhi",
  "category_slug": "dentists",
  "identity": {
    "name": "Dr. Meera's Dental Clinic",
    "city": "Delhi",
    "locality": "Lajpat Nagar",
    "verified": true
  },
  "subscription": {"status": "active", "plan": "Pro", "days_remaining": 82},
  "performance": {
    "views": 2410, "calls": 18, "ctr": 0.021, "leads": 9,
    "delta_7d": {"calls_pct": -0.05}
  },
  "offers": [...],
  "conversation_history": [...],
  "signals": ["stale_posts:22d", "ctr_below_peer_median"]
}
```

### TriggerContext
```python
{
  "id": "trg_001_research_digest_dentists",
  "scope": "merchant",
  "kind": "research_digest",
  "source": "external",
  "payload": {"category": "dentists", "top_item_id": "..."},
  "urgency": 2,
  "suppression_key": "research:dentists:2026-W17"
}
```

### CustomerContext (optional)
```python
{
  "customer_id": "c_001_priya_for_m001",
  "merchant_id": "m_001_drmeera_dentist_delhi",
  "relationship": {
    "first_visit": "2025-11-04",
    "last_visit": "2026-05-12",
    "visits_total": 4,
    "services_received": ["cleaning", "whitening"],
    "lifetime_value": 1696
  },
  "state": "lapsed_soft",
  "consent": {
    "scope": ["recall_reminders", "appointment_reminders"]
  }
}
```

## Trigger Types

| Kind | Scope | Example | Signal |
|------|-------|---------|--------|
| `research_digest` | merchant | JIDA research item | External knowledge |
| `recall_due` | customer | Patient is due for cleaning | Service lapse prevention |
| `perf_dip` | merchant | Calls dropped 50% | Growth recovery |
| `renewal_due` | merchant | Subscription expires in 12d | Retention |
| `festival_upcoming` | merchant | Diwali in 188 days | Seasonal opportunity |
| `regulation_change` | merchant | DCI compliance update | Legal awareness |

## Compose Strategy

The `Composer` class routes trigger kinds to specialized composers:

```python
def compose(category_ctx, merchant_ctx, trigger_ctx, customer_ctx=None):
    if trigger_kind == "research_digest":
        return _compose_research_digest(...)
    elif trigger_kind == "recall_due":
        return _compose_recall_reminder(...)
    elif trigger_kind == "perf_dip":
        return _compose_perf_alert(...)
    # ... etc
```

Each composer extracts relevant signals and constructs a **grounded, specific, high-engagement message**.

## Key Principles

1. **Service+price > discount** — "Haircut @ ₹99" outperforms "10% off"
2. **One signal wins** — Pick the best reason to message now
3. **Grounded > generic** — Use real merchant facts
4. **Category first** — Tone, voice, taboos vary by vertical
5. **Conversation continuity** — Track engagement history

## Testing

### Run Integration Test
```bash
python test_bot.py
```

### Run Judge Simulator
```bash
# Edit judge_simulator.py to set LLM_PROVIDER and LLM_API_KEY
python judge_simulator.py
```

The judge will:
1. Push 30 test scenarios
2. Score your bot on all 5 dimensions
3. Provide detailed feedback on each message

## Files

- `bot.py` — Main FastAPI server + Composer
- `requirements.txt` — Dependencies
- `test_bot.py` — Quick integration test
- `judge_simulator.py` — Official test harness (provided)
- `dataset/` — Seed data
  - `merchants_seed.json` — 10 merchants (→ 50)
  - `customers_seed.json` — 15 customers (→ 200)
  - `triggers_seed.json` — 25 triggers (→ 100)
  - `categories/` — Category knowledge (dentists, salons, etc.)

## Next Steps

1. **Enhance `_compose_*()` methods** — Replace placeholders with real logic
   - Extract merchant-specific signals
   - Select from offer_catalog
   - Match category voice
   - Compose compelling copy

2. **Add state management** — Track conversation continuity
   - Previous merchant replies
   - Engagement patterns
   - Message fatigue / suppression

3. **Implement offer selection** — Choose the right offer for the moment
   - Match trigger (festival → special offers)
   - Match merchant state (low CTR → free consultation)
   - Match customer state (lapsed → recall service)

4. **Tune for engagement** — A/B test different CTA types
   - `open_ended` — "Want ideas?"
   - `reply_yes_no` — "Book now?"
   - `click_link` — Link to action
   - `book_appointment` — Calendar integration

## Contact

For questions or issues, contact the magicpin AI Challenge team.
