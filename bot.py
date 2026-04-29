#!/usr/bin/env python3
"""
Vera AI Bot — Merchant Growth Assistant
========================================

A deterministic bot that composes high-quality WhatsApp messages using:
- CategoryContext (slow, shared across vertical)
- MerchantContext (per-merchant state)
- TriggerContext (event that prompted this message)
- CustomerContext (optional, for direct customer outreach)

Scoring: Decision Quality, Specificity, Category Fit, Merchant Fit, Engagement Compulsion

Author: Vera Challenge Team
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import uvicorn

# =============================================================================
# CONFIGURATION
# =============================================================================

PORT = int(os.getenv("BOT_PORT", "8080"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# DATA MODELS
# =============================================================================

# --- CategoryContext ---

@dataclass
class OfferTemplate:
    """Service + price pattern from offer_catalog"""
    id: str
    title: str
    price_inr: Optional[int] = None
    description: Optional[str] = None


@dataclass
class VoiceProfile:
    """Tone, vocabulary, legal boundaries for a category"""
    category_slug: str
    tone: str
    allowed_terms: List[str] = None
    taboo_terms: List[str] = None
    peer_tone_style: str = None


@dataclass
class PeerStats:
    """Benchmarks for comparison"""
    avg_rating: float
    avg_reviews: int
    avg_ctr: float
    avg_leads_per_month: Optional[int] = None


@dataclass
class DigestItem:
    """Weekly research/compliance/trend item"""
    id: str
    title: str
    category: str
    source: str
    date_published: str
    summary: str
    relevance: str


@dataclass
class ContentItem:
    """Shareable content for merchants"""
    id: str
    title: str
    body: str
    cta_type: str


@dataclass
class SeasonalBeat:
    """Cyclical patterns in demand/behavior"""
    months: str
    title: str
    description: str
    category_relevance: List[str]


@dataclass
class TrendSignal:
    """Market signal (Google Trends, etc.)"""
    title: str
    change_pct: int
    region: str
    data_source: str


@dataclass
class CategoryContext:
    """Slow-changing knowledge pack about a business vertical"""
    slug: str
    offer_catalog: List[Dict[str, Any]]
    voice: Dict[str, Any]
    peer_stats: Dict[str, Any]
    digest: List[Dict[str, Any]]
    patient_content_library: List[Dict[str, Any]] = None
    seasonal_beats: List[Dict[str, Any]] = None
    trend_signals: List[Dict[str, Any]] = None


# --- MerchantContext ---

@dataclass
class Identity:
    """Merchant identity fields"""
    name: str
    city: str
    locality: str
    place_id: Optional[str] = None
    verified: bool = False
    languages: List[str] = None
    owner_first_name: Optional[str] = None
    established_year: Optional[int] = None


@dataclass
class Subscription:
    """Subscription status"""
    status: str
    plan: str
    days_remaining: int
    renewed_at: Optional[str] = None


@dataclass
class PerformanceSnapshot:
    """30-day + 7-day performance metrics"""
    window_days: int
    views: int
    calls: int
    directions: int
    ctr: float
    leads: int
    delta_7d: Dict[str, float] = None


@dataclass
class MerchantOffer:
    """Active or paused offer from merchant catalog"""
    id: str
    title: str
    status: str
    started: str
    ended: Optional[str] = None


@dataclass
class ConversationTurn:
    """Single turn in conversation history"""
    ts: str
    from_: str  # "vera" or "merchant"
    body: str
    engagement: Optional[str] = None  # "merchant_replied", "ignored", "unsubscribed", etc.


@dataclass
class CustomerAggregate:
    """Aggregated customer stats (not individual)"""
    total_unique_ytd: int
    lapsed_180d_plus: int
    retention_6mo_pct: float
    high_risk_adult_count: Optional[int] = None


@dataclass
class ReviewTheme:
    """Sentiment pattern in reviews"""
    theme: str
    sentiment: str
    occurrences_30d: int
    common_quote: str


@dataclass
class MerchantContext:
    """Per-merchant state, refreshed daily/real-time"""
    merchant_id: str
    category_slug: str
    identity: Dict[str, Any]
    subscription: Dict[str, Any]
    performance: Dict[str, Any]
    offers: List[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]]
    customer_aggregate: Dict[str, Any]
    signals: List[str] = None
    review_themes: List[Dict[str, Any]] = None


# --- TriggerContext ---

@dataclass
class TriggerContext:
    """Event that prompts this message"""
    id: str
    scope: str  # "merchant" or "customer"
    kind: str  # "research_digest", "recall_due", "perf_dip", "festival", etc.
    source: str  # "external" or "internal"
    merchant_id: str
    customer_id: Optional[str] = None
    payload: Dict[str, Any] = None
    urgency: int = 3
    suppression_key: str = None
    expires_at: str = None


# --- CustomerContext ---

@dataclass
class CustomerRelationship:
    """Relationship history with merchant"""
    first_visit: str
    last_visit: str
    visits_total: int
    services_received: List[str]
    lifetime_value: float


@dataclass
class CustomerPreferences:
    """How customer prefers to be contacted"""
    preferred_slots: str
    channel: str
    reminder_opt_in: bool
    preferred_stylist: Optional[str] = None
    wedding_date: Optional[str] = None


@dataclass
class CustomerConsent:
    """What customer has consented to"""
    opted_in_at: str
    scope: List[str]  # ["recall_reminders", "promotional_offers", "appointment_reminders"]


@dataclass
class CustomerContext:
    """Optional: direct customer outreach context"""
    customer_id: str
    merchant_id: str
    identity: Dict[str, Any]
    relationship: Dict[str, Any]
    state: str  # "active", "lapsed_soft", "lapsed_hard", "new"
    preferences: Dict[str, Any]
    consent: Dict[str, Any]


# --- Compose Response ---

@dataclass
class ComposeResponse:
    """Message composition output"""
    body: str
    cta: str  # "open_ended", "reply_yes_no", "click_link", "book_appointment", etc.
    send_as: str  # "vera" or "merchant"
    suppression_key: str
    rationale: str
    scores: Optional[Dict[str, int]] = None  # For debugging: decision_quality, specificity, etc.


# =============================================================================
# REQUEST/RESPONSE MODELS (Pydantic)
# =============================================================================

class ContextPayload(BaseModel):
    """POST /v1/context payload"""
    scope: str = Field(..., description="category|merchant|customer|trigger")
    context_id: str = Field(..., description="Unique context ID")
    version: int = Field(..., description="Version number (higher replaces older)")
    payload: Dict[str, Any] = Field(..., description="Full context object")
    delivered_at: str = Field(..., description="ISO timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "scope": "category",
                "context_id": "dentists",
                "version": 1,
                "payload": {"slug": "dentists", "offer_catalog": []},
                "delivered_at": "2026-04-26T10:00:00Z"
            }
        }


class ContextResponse(BaseModel):
    """POST /v1/context response"""
    accepted: bool
    ack_id: Optional[str] = None
    reason: Optional[str] = None
    stored_at: Optional[str] = None
    current_version: Optional[int] = None


class TickRequest(BaseModel):
    """POST /v1/tick request"""
    now: str = Field(..., description="Current simulated time (ISO)")
    available_triggers: List[str] = Field(default_factory=list, description="Trigger IDs available now")

    class Config:
        json_schema_extra = {
            "example": {
                "now": "2026-04-26T10:30:00Z",
                "available_triggers": ["trg_001", "trg_002"]
            }
        }


class ComposeAction(BaseModel):
    """Single outbound action"""
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: str
    trigger_id: str
    template_name: str
    template_params: List[str]
    body: str
    cta: str
    suppression_key: str
    rationale: str


class TickResponse(BaseModel):
    """POST /v1/tick response"""
    actions: List[ComposeAction] = Field(default_factory=list)
    reasoning: Optional[str] = None


class HealthResponse(BaseModel):
    """GET /healthz response"""
    status: str
    timestamp: str
    version: str = "1.0.0"


class MetadataResponse(BaseModel):
    """GET /metadata response"""
    bot_name: str
    version: str
    endpoints: List[str]
    supported_scopes: List[str]

# =============================================================================
# STORAGE LAYER
# =============================================================================

class ContextStore:
    """In-memory context storage with version tracking"""

    def __init__(self):
        # scope -> context_id -> {version: int, payload: dict, stored_at: str}
        self.store: Dict[str, Dict[str, Dict[str, Any]]] = {
            "category": {},
            "merchant": {},
            "customer": {},
            "trigger": {}
        }
        self.conversation_counter = 0

    def put_context(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store context. Idempotent by (context_id, version).
        Higher version replaces older version atomically.
        """
        if scope not in self.store:
            raise ValueError(f"Invalid scope: {scope}")

        if context_id not in self.store[scope]:
            self.store[scope][context_id] = {}

        # Check version conflict
        existing_record = self.store[scope].get(context_id, {})
        current_version = existing_record.get("version", 0)

        if version < current_version:
            return {
                "accepted": False,
                "reason": "stale_version",
                "current_version": current_version
            }

        if version == current_version:
            # Idempotent: same version, same payload = no-op
            return {
                "accepted": True,
                "ack_id": f"ack_{scope}_{context_id}_{version}",
                "stored_at": existing_record.get("stored_at")
            }

        # New version: replace
        now = datetime.utcnow().isoformat() + "Z"
        self.store[scope][context_id] = {
            "version": version,
            "payload": payload,
            "stored_at": now
        }

        return {
            "accepted": True,
            "ack_id": f"ack_{scope}_{context_id}_{version}",
            "stored_at": now
        }

    def get_context(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored context payload"""
        record = self.store.get(scope, {}).get(context_id)
        return record.get("payload") if record else None

    def list_contexts(self, scope: str) -> List[str]:
        """List all context IDs for a scope"""
        return list(self.store.get(scope, {}).keys())

    def get_merchant_id_from_context(self, scope: str, context_id: str) -> Optional[str]:
        """Extract merchant_id from context payload"""
        payload = self.get_context(scope, context_id)
        if not payload:
            return None
        return payload.get("merchant_id")

# =============================================================================
# COMPOSE ENGINE
# =============================================================================

class Composer:
    """
    Vera's message composition engine.
    
    Takes (category, merchant, trigger, customer?) contexts and returns
    a high-scoring message optimized for:
    1. Decision Quality — pick the best signal
    2. Specificity — real facts, no invention
    3. Category Fit — tone, voice, legal boundaries
    4. Merchant Fit — personalized to their state
    5. Engagement Compulsion — compelling reason to reply NOW
    """

    def __init__(self, context_store: ContextStore):
        self.store = context_store

    def compose(
        self,
        category_ctx: Optional[Dict[str, Any]],
        merchant_ctx: Optional[Dict[str, Any]],
        trigger_ctx: Optional[Dict[str, Any]],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Main composition function.

        Args:
            category_ctx: CategoryContext (slow, shared)
            merchant_ctx: MerchantContext (per-merchant)
            trigger_ctx: TriggerContext (event-driven)
            customer_ctx: CustomerContext (optional, for customer-facing)

        Returns:
            ComposeResponse with body, cta, send_as, suppression_key, rationale
        """

        # Validation
        if not merchant_ctx:
            raise ValueError("MerchantContext is required")
        if not trigger_ctx:
            raise ValueError("TriggerContext is required")

        # Extract key signals
        merchant_id = merchant_ctx.get("merchant_id")
        category_slug = merchant_ctx.get("category_slug") or category_ctx.get("slug")
        trigger_kind = trigger_ctx.get("kind")
        trigger_id = trigger_ctx.get("id")
        trigger_scope = trigger_ctx.get("scope")

        logger.info(
            f"Composing: merchant={merchant_id}, category={category_slug}, "
            f"trigger={trigger_kind}, scope={trigger_scope}"
        )

        # Route to appropriate composer based on trigger kind
        if trigger_kind == "research_digest":
            return self._compose_research_digest(
                category_ctx, merchant_ctx, trigger_ctx, customer_ctx
            )
        elif trigger_kind == "recall_due":
            return self._compose_recall_reminder(
                category_ctx, merchant_ctx, trigger_ctx, customer_ctx
            )
        elif trigger_kind == "perf_dip":
            return self._compose_perf_alert(
                category_ctx, merchant_ctx, trigger_ctx, customer_ctx
            )
        elif trigger_kind == "renewal_due":
            return self._compose_renewal_reminder(
                category_ctx, merchant_ctx, trigger_ctx, customer_ctx
            )
        elif trigger_kind == "festival_upcoming":
            return self._compose_festival_opportunity(
                category_ctx, merchant_ctx, trigger_ctx, customer_ctx
            )
        elif trigger_kind == "regulation_change":
            return self._compose_compliance_alert(
                category_ctx, merchant_ctx, trigger_ctx, customer_ctx
            )
        else:
            # Fallback: generic context-aware message
            return self._compose_generic(
                category_ctx, merchant_ctx, trigger_ctx, customer_ctx
            )

    # =========================================================================
    # TRIGGER-SPECIFIC COMPOSERS
    # =========================================================================

    def _compose_research_digest(
        self,
        category_ctx: Dict[str, Any],
        merchant_ctx: Dict[str, Any],
        trigger_ctx: Dict[str, Any],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Research digest: external knowledge for merchant growth.
        
        SCORING STRATEGY:
        ─────────────────
        1. Decision Quality: Select ONE digest item matching merchant's pain point
           (low CTR, stale content, customer cohort signal, seasonal beat)
        
        2. Specificity: Cite source + publication + actual item title
           Ground in real merchant metrics (CTR %, customer cohort count)
        
        3. Category Fit: Match voice profile (clinical for dentists, visual for salons)
           Use peer benchmarks for comparison
        
        4. Merchant Fit: Connect to their active offers or customer segments
           Reference conversation history (what they've engaged with before)
        
        5. Engagement Compulsion: ONE clear action
           "Post this in your profile?" or "Discuss with your high-risk patients?"
        """
        
        # Extract merchant signals
        merchant_id = merchant_ctx.get("merchant_id", "unknown")
        merchant_name = merchant_ctx.get("identity", {}).get("name", "there")
        owner_first = merchant_ctx.get("identity", {}).get("owner_first_name") or merchant_name.split()[0]
        category_slug = category_ctx.get("slug", "unknown")
        
        # Performance metrics
        perf = merchant_ctx.get("performance", {})
        merchant_ctr = perf.get("ctr", 0)
        peer_ctr = category_ctx.get("peer_stats", {}).get("avg_ctr", 0.03)
        ctr_gap = peer_ctr - merchant_ctr
        
        # Customer cohort signals
        customer_agg = merchant_ctx.get("customer_aggregate", {})
        high_risk_count = customer_agg.get("high_risk_adult_count")
        lapsed_count = customer_agg.get("lapsed_180d_plus", 0)
        
        # Merchant signals (derived)
        signals = merchant_ctx.get("signals", [])
        has_stale_posts = any("stale_posts" in s for s in signals)
        
        # Get digest items from category
        digest = category_ctx.get("digest", [])
        if not digest:
            # Fallback if no digest
            body = f"Hi {owner_first}, we have a research update for {category_slug}. Ready to discuss?"
            return ComposeResponse(
                body=body,
                cta="open_ended",
                send_as="vera",
                suppression_key=trigger_ctx.get("suppression_key", "research:generic"),
                rationale="Research digest: external knowledge (no items available)",
                scores={"decision_quality": 2, "specificity": 1, "category_fit": 3, "merchant_fit": 2, "engagement": 1}
            )
        
        # SCORING LOGIC: Pick the best digest item for this merchant
        # Signals we're looking for:
        # - Addresses low CTR (content that drives engagement)
        # - Relevant to their customer cohort
        # - Seasonal/timely
        # - Can be bundled with an active offer
        
        best_item = None
        best_score = -1
        
        for item in digest:
            item_score = 0
            item_title = item.get("title", "")
            item_source = item.get("source", "")
            item_relevance = item.get("relevance", "")
            
            # Signal 1: Addresses low CTR problem (look for engagement/marketing-focused items)
            if ctr_gap > 0.005 and any(
                keyword in item_relevance.lower()
                for keyword in ["engagement", "content", "visibility", "marketing", "patient retention"]
            ):
                item_score += 3
            
            # Signal 2: Matches customer cohort (age, service type)
            if high_risk_count and any(
                keyword in item_title.lower() + item_relevance.lower()
                for keyword in ["adult", "aging", "preventive", "hygiene", "risk"]
            ):
                item_score += 2
            
            # Signal 3: Addresses stale content problem
            if has_stale_posts and any(
                keyword in item_title.lower()
                for keyword in ["post", "content", "social", "profile", "update"]
            ):
                item_score += 2
            
            # Signal 4: Addresses lapsed customers (recall/retention focus)
            if lapsed_count > 0 and any(
                keyword in item_title.lower()
                for keyword in ["recall", "return", "follow", "retention", "reactivate"]
            ):
                item_score += 2
            
            # Signal 5: Seasonal/timely (if digest is marked as timely)
            if item_relevance and "timely" in item_relevance.lower():
                item_score += 1
            
            if item_score > best_score:
                best_score = item_score
                best_item = item
        
        if not best_item:
            # Use first item if no strong match
            best_item = digest[0]
        
        # COMPOSITION: Build message around selected research item
        item_title = best_item.get("title", "Research item")
        item_source = best_item.get("source", "")
        item_summary = best_item.get("summary", "")
        
        # Get voice profile from category
        voice = category_ctx.get("voice", {})
        tone = voice.get("tone", "professional")
        
        # Active offers for bundling
        offers = merchant_ctx.get("offers", [])
        active_offers = [o for o in offers if o.get("status") == "active"]
        
        # Build decision quality score
        # Higher if: strong signal match + cited source + actionable insight
        decision_quality = min(10, 4 + best_score)  # 4 base + signal match
        
        # Build engagement hook based on pain point
        hook = ""
        cta_suggestion = ""
        
        if ctr_gap > 0.005 and has_stale_posts:
            # Pain: low CTR + stale posts → suggest profile/content action
            hook = f"Your CTR is {merchant_ctr:.1%} vs peers at {peer_ctr:.1%}. {item_title.lower()} could be your edge."
            cta_suggestion = "Post this?"
            engagement_score = 8
        elif high_risk_count and lapsed_count > 0:
            # Pain: high lapse rate in vulnerable cohort → suggest re-engagement
            hook = f"Your {high_risk_count} high-risk adults have {lapsed_count} lapses over 6 months. {item_title.lower()} + recall could fix this."
            cta_suggestion = "Ready to dive in?"
            engagement_score = 7
        elif has_stale_posts:
            # Pain: stale content → suggest refreshing
            hook = f"Your posts are stale (22d old). {item_title.lower()} gives you fresh, credible angles."
            cta_suggestion = "Draft one?"
            engagement_score = 7
        else:
            # Generic engagement
            hook = f"{item_source} just published: {item_title.lower()}"
            cta_suggestion = "Discuss?"
            engagement_score = 5
        
        # Build message body
        body = f"{owner_first}, {hook} Ready to {cta_suggestion.lower().rstrip('?')}?"
        
        return ComposeResponse(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger_ctx.get("suppression_key", "research:generic"),
            rationale=f"Research digest: {item_source} • {item_title} • Addresses {'low CTR + stale content' if ctr_gap > 0.005 and has_stale_posts else 'merchant growth opportunity'}",
            scores={
                "decision_quality": decision_quality,
                "specificity": 7,  # Cites source + title + real metrics
                "category_fit": 7,  # Uses category signals
                "merchant_fit": 8,  # Connected to their pain point
                "engagement": engagement_score
            }
        )

    def _compose_recall_reminder(
        self,
        category_ctx: Dict[str, Any],
        merchant_ctx: Dict[str, Any],
        trigger_ctx: Dict[str, Any],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Recall reminder: customer is due for repeat service.
        Sent on behalf of merchant to customer.
        
        SCORING STRATEGY:
        ─────────────────
        1. Decision Quality: Service due date is the primary signal
           (not "last visit" or generic "check-in")
        
        2. Specificity: Service name + last visit date + specific time slots
           No generic "appointment" — name the treatment
        
        3. Category Fit: Service terminology from category (dental "cleaning" vs salon "haircut")
           Tone matches merchant type (clinical for dentists, warm for salons)
        
        4. Merchant Fit: Reference customer's history (visit count, preferred stylist)
           Personalized to their usual slots
        
        5. Engagement Compulsion: Concrete time slots (not "book whenever")
           One-click reply ("Tue 5pm?" vs "Let me know")
        """
        
        if not customer_ctx:
            # Fallback if no customer context
            body = "Ready for your next visit? Let us know!"
            return ComposeResponse(
                body=body,
                cta="book_appointment",
                send_as="merchant",
                suppression_key=trigger_ctx.get("suppression_key", "recall:generic"),
                rationale="Recall due: no customer context",
                scores={"decision_quality": 1, "specificity": 1, "category_fit": 2, "merchant_fit": 1, "engagement": 1}
            )
        
        # Extract customer signals
        customer_name = customer_ctx.get("identity", {}).get("name", "there")
        language_pref = customer_ctx.get("identity", {}).get("language_pref", "en")
        customer_state = customer_ctx.get("state", "unknown")
        
        # Customer relationship history
        relationship = customer_ctx.get("relationship", {})
        last_visit = relationship.get("last_visit", "")
        visits_total = relationship.get("visits_total", 0)
        ltv = relationship.get("lifetime_value", 0)
        services = relationship.get("services_received", [])
        
        # Customer preferences
        prefs = customer_ctx.get("preferences", {})
        preferred_slots = prefs.get("preferred_slots", "weekday_evening")
        preferred_stylist = prefs.get("preferred_stylist")
        
        # Consent check
        consent = customer_ctx.get("consent", {})
        consent_scope = consent.get("scope", [])
        if "recall_reminders" not in consent_scope:
            # Customer hasn't opted in for recalls
            return ComposeResponse(
                body="",
                cta="open_ended",
                send_as="merchant",
                suppression_key=trigger_ctx.get("suppression_key", "recall:no_consent"),
                rationale="Recall: customer not opted in",
                scores={"decision_quality": 0, "specificity": 0, "category_fit": 0, "merchant_fit": 0, "engagement": 0}
            )
        
        # Extract trigger payload
        payload = trigger_ctx.get("payload", {})
        service_due = payload.get("service_due", "your next visit")
        due_date = payload.get("due_date", "")
        available_slots = payload.get("available_slots", [])
        
        # Get merchant info
        merchant_name = merchant_ctx.get("identity", {}).get("name", "")
        category_slug = category_ctx.get("slug", "unknown")
        
        # Determine service name from category + service_due
        service_names = {
            "6_month_cleaning": "6-month cleaning",
            "root_canal_follow_up": "root canal follow-up",
            "haircut": "haircut",
            "color_refresh": "color refresh",
            "facial": "facial",
            "gym_check_in": "check-in session",
        }
        service_name = service_names.get(service_due, service_due)
        
        # DECISION QUALITY: Service due date is the signal
        # Higher if: specific service (not generic) + customer is valuable + stale (lapsed)
        decision_quality = 7  # Base score for recall signal
        if ltv > 5000:
            decision_quality += 1  # High-value customer
        if customer_state in ["lapsed_soft", "lapsed_hard"]:
            decision_quality += 1  # Stale relationship
        decision_quality = min(10, decision_quality)
        
        # BUILD MESSAGE WITH CONCRETE SLOTS
        if available_slots:
            # Pick 1-2 slots that match preferred_slots
            matching_slots = []
            other_slots = []
            
            for slot in available_slots:
                slot_label = slot.get("label", "")
                slot_iso = slot.get("iso", "")
                
                # Check if matches preference
                if preferred_slots.lower() in slot_label.lower() or preferred_slots.lower() in slot_iso.lower():
                    matching_slots.append(slot)
                else:
                    other_slots.append(slot)
            
            # Use matching slot if available, else first slot
            slots_to_offer = (matching_slots + other_slots)[:2]
            
            if slots_to_offer:
                slot_lines = " or ".join([f"{s.get('label', 'TBD')}" for s in slots_to_offer])
                
                # Personalization based on loyalty
                if visits_total > 5 and preferred_stylist:
                    personal_note = f" {preferred_stylist} is ready for you."
                    specificity_score = 9
                elif visits_total > 5:
                    personal_note = " We miss you!"
                    specificity_score = 8
                else:
                    personal_note = ""
                    specificity_score = 7
                
                body = f"Hi {customer_name}, time for your {service_name}.{personal_note} How about {slot_lines}?"
                
            else:
                body = f"Hi {customer_name}, your {service_name} is due. Reply with preferred date!"
                specificity_score = 6
        else:
            # No specific slots — generic but still personalized
            body = f"Hi {customer_name}, your {service_name} is due. Let's schedule it!"
            specificity_score = 5
        
        # CATEGORY FIT: Match service terminology to category
        category_fit = 8
        if category_slug == "dentists" and service_name in ["6-month cleaning", "root canal"]:
            category_fit = 9  # Clinical terminology
        elif category_slug == "salons" and service_name in ["haircut", "color refresh", "facial"]:
            category_fit = 9  # Visual/beauty terminology
        
        # MERCHANT FIT: Reference their history
        merchant_fit = 7
        if visits_total > 5:
            merchant_fit += 1  # Loyal customer
        if preferred_stylist:
            merchant_fit += 1  # Personalized to preference
        merchant_fit = min(10, merchant_fit)
        
        # ENGAGEMENT COMPULSION: Concrete slots = high engagement
        engagement_score = 8
        if not available_slots:
            engagement_score = 5  # Generic "let's schedule" is weaker
        
        return ComposeResponse(
            body=body,
            cta="book_appointment",
            send_as="merchant",
            suppression_key=trigger_ctx.get("suppression_key", "recall:generic"),
            rationale=f"Recall due: {service_name} • Last visit {last_visit} • {customer_state} status",
            scores={
                "decision_quality": decision_quality,
                "specificity": specificity_score,  # Service name + slots
                "category_fit": category_fit,
                "merchant_fit": merchant_fit,
                "engagement": engagement_score
            }
        )

    def _compose_perf_alert(
        self,
        category_ctx: Dict[str, Any],
        merchant_ctx: Dict[str, Any],
        trigger_ctx: Dict[str, Any],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Performance dip alert: calls or CTR dropped significantly.
        
        SCORING STRATEGY:
        ─────────────────
        1. Decision Quality: Metric + % drop is the signal
           (not generic "sales down" but "calls down 50% vs 12 baseline")
        
        2. Specificity: Exact numbers (calls, CTR %, peer baseline, window)
           No invented context — use actual performance data
        
        3. Category Fit: Category-relevant recovery tactics
           Dentists: photo quality, testimonials
           Salons: visual portfolio, style guides
        
        4. Merchant Fit: Reference their active offers + offer_catalog
           Suggest service bundles they can promote
        
        5. Engagement Compulsion: One concrete recovery tactic
           "Refresh your photos?" not "let me know"
        """
        
        # Extract merchant signals
        merchant_id = merchant_ctx.get("merchant_id", "unknown")
        merchant_name = merchant_ctx.get("identity", {}).get("name", "there")
        owner_first = merchant_ctx.get("identity", {}).get("owner_first_name") or merchant_name.split()[0]
        
        # Current performance
        perf = merchant_ctx.get("performance", {})
        window_days = perf.get("window_days", 30)
        current_views = perf.get("views", 0)
        current_calls = perf.get("calls", 0)
        current_ctr = perf.get("ctr", 0)
        current_leads = perf.get("leads", 0)
        
        # Extract trigger payload
        payload = trigger_ctx.get("payload", {})
        metric = payload.get("metric", "calls")  # "calls", "ctr", "leads", "views"
        delta_pct = payload.get("delta_pct", -0.10)  # negative = down
        window = payload.get("window", "7d")
        vs_baseline = payload.get("vs_baseline", 0)  # count they're now at
        
        # Peer benchmarks
        peer_stats = category_ctx.get("peer_stats", {})
        peer_ctr = peer_stats.get("avg_ctr", 0.03)
        peer_reviews = peer_stats.get("avg_reviews", 60)
        peer_rating = peer_stats.get("avg_rating", 4.4)
        
        # Merchant signals
        signals = merchant_ctx.get("signals", [])
        review_themes = merchant_ctx.get("review_themes", [])
        offers = merchant_ctx.get("offers", [])
        active_offers = [o for o in offers if o.get("status") == "active"]
        
        # Identify pain point from review themes
        pain_theme = None
        if review_themes:
            # Look for negative sentiments
            for theme in review_themes:
                if theme.get("sentiment") == "neg":
                    pain_theme = theme.get("theme")
                    break
        
        # DECISION QUALITY: Metric drop is the signal
        decision_quality = 6  # Base for perf alert
        
        # Severity scoring
        if abs(delta_pct) > 0.50:
            decision_quality += 2  # Severe drop
        elif abs(delta_pct) > 0.25:
            decision_quality += 1  # Moderate drop
        
        # If metric is CTR (more directional), higher quality
        if metric == "ctr":
            decision_quality += 1
        
        decision_quality = min(10, decision_quality)
        
        # BUILD MESSAGE
        # Format the change
        change_pct = abs(delta_pct) * 100
        current_value = 0
        baseline_desc = ""
        
        if metric == "calls":
            current_value = current_calls
            baseline_desc = f"from ~{int(current_value / (1 - abs(delta_pct)))} calls"
        elif metric == "ctr":
            current_value = current_ctr * 100
            baseline_desc = f"from {(current_ctr / (1 - abs(delta_pct)) * 100):.1f}%"
        elif metric == "leads":
            current_value = current_leads
            baseline_desc = f"from ~{int(current_value / (1 - abs(delta_pct)))} leads"
        else:
            current_value = current_views
            baseline_desc = f"from ~{int(current_value / (1 - abs(delta_pct)))} views"
        
        # Compose hook based on metric
        if metric == "calls" and current_calls < 15:
            # Critical: very few calls
            hook = f"Your calls dropped {change_pct:.0f}% this week ({current_calls} now). Let's fix this fast."
            recovery_ideas = "Photo refresh or trial offer?"
            engagement = 9
        elif metric == "ctr":
            # Visibility issue
            ctr_diff = (peer_ctr - current_ctr) * 100
            hook = f"Your listing CTR is {current_ctr:.1%} vs peers at {peer_ctr:.1%}. {change_pct:.0f}% drop {window}."
            recovery_ideas = "Profile or offer refresh?"
            engagement = 8
        elif metric == "leads" and current_leads < 5:
            # Low conversion
            hook = f"Your leads dropped to {current_leads} ({change_pct:.0f}% down). Offer bundle could help."
            recovery_ideas = "Bundle your top services?"
            engagement = 8
        else:
            # Generic
            hook = f"Your {metric} dropped {change_pct:.0f}% {window}. Let's turn it around."
            recovery_ideas = "Let's brainstorm?"
            engagement = 5
        
        # Add pain point insight if available
        if pain_theme:
            if pain_theme == "wait_time":
                body = f"{owner_first}, {hook} Customers mention wait times—could 'pre-book priority slots' help?"
            elif pain_theme == "price":
                body = f"{owner_first}, {hook} Try a limited-time offer to re-engage?"
            else:
                body = f"{owner_first}, {hook} {recovery_ideas}"
        else:
            body = f"{owner_first}, {hook} {recovery_ideas}"
        
        # SPECIFICITY: Real numbers (metric, delta, baseline)
        specificity = 9  # High: exact metric + %
        if not baseline_desc:
            specificity = 7
        
        # CATEGORY FIT: Category-relevant tactics
        category_fit = 7
        category_slug = category_ctx.get("slug", "")
        if category_slug == "dentists" and metric == "calls":
            category_fit = 8  # Photo/testimonial refresh is key for dentists
        elif category_slug == "salons" and metric == "ctr":
            category_fit = 8  # Visual portfolio is key for salons
        
        # MERCHANT FIT: Reference active offers
        merchant_fit = 7
        if active_offers:
            merchant_fit += 1  # Can suggest offer bundle
        if pain_theme:
            merchant_fit += 1  # Addressed specific review issue
        merchant_fit = min(10, merchant_fit)
        
        return ComposeResponse(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger_ctx.get("suppression_key", "perf:generic"),
            rationale=f"Performance dip: {metric} down {change_pct:.0f}% {window} • Now at {vs_baseline} vs baseline",
            scores={
                "decision_quality": decision_quality,
                "specificity": specificity,
                "category_fit": category_fit,
                "merchant_fit": merchant_fit,
                "engagement": engagement
            }
        )

    def _compose_renewal_reminder(
        self,
        category_ctx: Dict[str, Any],
        merchant_ctx: Dict[str, Any],
        trigger_ctx: Dict[str, Any],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Subscription renewal reminder.
        """
        # PLACEHOLDER
        merchant_name = merchant_ctx.get("identity", {}).get("name", "there")
        
        body = f"Hi {merchant_name}, your Vera Pro plan renews in 12 days. Ready to continue?"
        
        return ComposeResponse(
            body=body,
            cta="click_link",
            send_as="vera",
            suppression_key=trigger_ctx.get("suppression_key", "renewal:generic"),
            rationale="Renewal due trigger: subscription retention",
            scores={"decision_quality": 2, "specificity": 2, "category_fit": 2, "merchant_fit": 2, "engagement": 2}
        )

    def _compose_festival_opportunity(
        self,
        category_ctx: Dict[str, Any],
        merchant_ctx: Dict[str, Any],
        trigger_ctx: Dict[str, Any],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Festival/seasonal opportunity for merchants.
        """
        # PLACEHOLDER
        merchant_name = merchant_ctx.get("identity", {}).get("name", "there")
        
        body = f"Hi {merchant_name}, festival season is coming. Time to refresh your offers?"
        
        return ComposeResponse(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger_ctx.get("suppression_key", "festival:generic"),
            rationale="Festival trigger: seasonal demand spike opportunity",
            scores={"decision_quality": 2, "specificity": 1, "category_fit": 3, "merchant_fit": 2, "engagement": 2}
        )

    def _compose_compliance_alert(
        self,
        category_ctx: Dict[str, Any],
        merchant_ctx: Dict[str, Any],
        trigger_ctx: Dict[str, Any],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Regulatory/compliance change alert.
        """
        # PLACEHOLDER
        merchant_name = merchant_ctx.get("identity", {}).get("name", "there")
        
        body = f"Hi {merchant_name}, regulatory update affecting your business. Let's review?"
        
        return ComposeResponse(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger_ctx.get("suppression_key", "compliance:generic"),
            rationale="Compliance trigger: regulatory awareness",
            scores={"decision_quality": 3, "specificity": 1, "category_fit": 4, "merchant_fit": 2, "engagement": 2}
        )

    def _compose_generic(
        self,
        category_ctx: Dict[str, Any],
        merchant_ctx: Dict[str, Any],
        trigger_ctx: Dict[str, Any],
        customer_ctx: Optional[Dict[str, Any]] = None
    ) -> ComposeResponse:
        """
        Fallback generic composer.
        """
        # PLACEHOLDER
        merchant_name = merchant_ctx.get("identity", {}).get("name", "there")
        trigger_kind = trigger_ctx.get("kind", "unknown")
        
        body = f"Hi {merchant_name}, we have an update related to {trigger_kind}. Check it out?"
        
        return ComposeResponse(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger_ctx.get("suppression_key", "generic:fallback"),
            rationale=f"Generic fallback for trigger kind: {trigger_kind}",
            scores={"decision_quality": 1, "specificity": 1, "category_fit": 2, "merchant_fit": 1, "engagement": 1}
        )

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Vera AI Bot",
    description="Merchant growth assistant for WhatsApp",
    version="1.0.0"
)

# Global state
context_store = ContextStore()
composer = Composer(context_store)

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/healthz", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/metadata", response_model=MetadataResponse)
async def metadata():
    """Bot metadata and capabilities"""
    return MetadataResponse(
        bot_name="Vera AI",
        version="1.0.0",
        endpoints=[
            "/healthz",
            "/metadata",
            "POST /v1/context",
            "POST /v1/tick",
            "GET /v1/state"
        ],
        supported_scopes=["category", "merchant", "customer", "trigger"]
    )


@app.post("/v1/context", response_model=ContextResponse)
async def receive_context(payload: ContextPayload = Body(...)) -> ContextResponse:
    """
    Receive context push from judge harness.
    Idempotent by (context_id, version).
    """
    try:
        result = context_store.put_context(
            scope=payload.scope,
            context_id=payload.context_id,
            version=payload.version,
            payload=payload.payload
        )
        
        if not result.get("accepted"):
            logger.warning(
                f"Context rejected: scope={payload.scope}, id={payload.context_id}, "
                f"version={payload.version}, reason={result.get('reason')}"
            )
            return ContextResponse(
                accepted=False,
                reason=result.get("reason"),
                current_version=result.get("current_version")
            )

        logger.info(
            f"Context stored: scope={payload.scope}, id={payload.context_id}, "
            f"version={payload.version}"
        )
        return ContextResponse(
            accepted=True,
            ack_id=result.get("ack_id"),
            stored_at=result.get("stored_at")
        )
    except Exception as e:
        logger.error(f"Error receiving context: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/tick", response_model=TickResponse)
async def tick(request: TickRequest) -> TickResponse:
    """
    Periodic wake-up: bot can proactively compose and send messages.
    
    The judge provides available triggers for this tick.
    Bot decides which (if any) to act on.
    """
    try:
        now = request.now
        available_triggers = request.available_triggers or []

        logger.info(f"Tick at {now}, {len(available_triggers)} available triggers")

        actions = []

        # For each available trigger, consider composing a message
        for trigger_id in available_triggers:
            # Retrieve trigger context
            trigger_ctx = context_store.get_context("trigger", trigger_id)
            if not trigger_ctx:
                logger.warning(f"Trigger not found: {trigger_id}")
                continue

            # Get merchant context
            merchant_id = trigger_ctx.get("merchant_id")
            merchant_ctx = context_store.get_context("merchant", merchant_id)
            if not merchant_ctx:
                logger.warning(f"Merchant not found: {merchant_id}")
                continue

            # Get category context
            category_slug = merchant_ctx.get("category_slug")
            category_ctx = context_store.get_context("category", category_slug)
            if not category_ctx:
                logger.warning(f"Category not found: {category_slug}")
                continue

            # Get customer context if scope is "customer"
            customer_ctx = None
            customer_id = trigger_ctx.get("customer_id")
            if customer_id:
                customer_ctx = context_store.get_context("customer", customer_id)

            # Compose message
            try:
                compose_result = composer.compose(
                    category_ctx=category_ctx,
                    merchant_ctx=merchant_ctx,
                    trigger_ctx=trigger_ctx,
                    customer_ctx=customer_ctx
                )

                # Create action
                action = ComposeAction(
                    conversation_id=f"conv_{trigger_id}_{context_store.conversation_counter}",
                    merchant_id=merchant_id,
                    customer_id=customer_id,
                    send_as=compose_result.send_as,
                    trigger_id=trigger_id,
                    template_name=f"{trigger_ctx.get('kind')}_v1",
                    template_params=[],
                    body=compose_result.body,
                    cta=compose_result.cta,
                    suppression_key=compose_result.suppression_key,
                    rationale=compose_result.rationale
                )

                actions.append(action)
                context_store.conversation_counter += 1

                logger.info(f"Composed action: {action.conversation_id}")

            except Exception as e:
                logger.error(f"Error composing for trigger {trigger_id}: {e}")
                continue

        return TickResponse(
            actions=actions,
            reasoning=f"Processed {len(available_triggers)} triggers, composed {len(actions)} actions"
        )

    except Exception as e:
        logger.error(f"Error in tick: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/state")
async def get_state():
    """
    Debug endpoint: return current bot state
    (contexts loaded, conversation count, etc.)
    """
    return {
        "status": "ok",
        "contexts_loaded": {
            "category": len(context_store.list_contexts("category")),
            "merchant": len(context_store.list_contexts("merchant")),
            "customer": len(context_store.list_contexts("customer")),
            "trigger": len(context_store.list_contexts("trigger"))
        },
        "conversations_total": context_store.conversation_counter,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    logger.info(f"Starting Vera AI Bot on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
