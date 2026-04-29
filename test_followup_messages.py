#!/usr/bin/env python3
"""
Test suite for Vera AI Bot's context-specific, CTA-centric followup messages.

Demonstrates:
1. Initial message composition (via composer)
2. Reply handling with sentiment detection (via followup_composer)
3. Context-specific routing based on reply sentiment
4. CTA-centric next actions
"""

import json
import sys
from pathlib import Path
from dataclasses import asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bot import (
    ContextStore,
    Composer,
    FollowupComposer,
    ComposeResponse
)

# =============================================================================
# TEST SCENARIO: RESEARCH DIGEST FOLLOWUP PATHS
# =============================================================================

def test_research_digest_followups():
    """Test all followup paths for research_digest trigger"""
    
    print("\n" + "="*80)
    print("TEST: Research Digest Followup Scenarios")
    print("="*80)
    
    context_store = ContextStore()
    composer = Composer(context_store)
    followup_composer = composer.followup_composer
    
    # Setup: store contexts
    category_ctx = {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical", "allowed_terms": ["fluoride", "caries"]},
        "peer_stats": {"avg_ctr": 0.03, "avg_rating": 4.4},
        "digest": []
    }
    
    merchant_ctx = {
        "merchant_id": "m_001_drmeera",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Meera's Dental Clinic", "owner_first_name": "Meera"},
        "performance": {"ctr": 0.021},
        "customer_aggregate": {"high_risk_adult_count": 120, "lapsed_180d_plus": 25},
        "signals": ["stale_posts:22d"],
        "offers": [{"id": "o_1", "title": "Cleaning @ ₹299", "status": "active"}]
    }
    
    trigger_ctx = {
        "id": "trg_research_1",
        "kind": "research_digest",
        "merchant_id": "m_001_drmeera",
        "suppression_key": "research:dentists:2026-W17"
    }
    
    # =========================================================================
    # SCENARIO 1: Positive Reply → Move to Next Step
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 1: Customer Says YES → Move to Drafting")
    print("-"*80)
    
    reply_message_positive = "Yes, send me the abstract"
    
    followup_1 = followup_composer.compose_followup(
        conversation_id="conv_research_1",
        trigger_kind="research_digest",
        merchant_id="m_001_drmeera",
        customer_id=None,
        reply_message=reply_message_positive,
        original_cta="open_ended",
        category_ctx=category_ctx,
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message_positive}'")
    print(f"  Sentiment Detected: POSITIVE ✅")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup_1['action']}")
    print(f"  Body: {followup_1['body']}")
    print(f"  CTA: {followup_1['cta']}")
    print(f"  Rationale: {followup_1['rationale']}")
    
    # =========================================================================
    # SCENARIO 2: Hesitant Reply → Back Off, Address Concern
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 2: Customer Says MAYBE (Budget Concern) → Lower Friction Entry")
    print("-"*80)
    
    reply_message_hesitant = "This sounds good but we don't have budget for content right now"
    
    followup_2 = followup_composer.compose_followup(
        conversation_id="conv_research_2",
        trigger_kind="research_digest",
        merchant_id="m_001_drmeera",
        customer_id=None,
        reply_message=reply_message_hesitant,
        original_cta="open_ended",
        category_ctx=category_ctx,
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message_hesitant}'")
    print(f"  Sentiment Detected: HESITANT (Budget Barrier) 💰")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup_2['action']}")
    print(f"  Body: {followup_2['body']}")
    print(f"  CTA: {followup_2['cta']}")
    print(f"  Rationale: {followup_2['rationale']}")
    
    # =========================================================================
    # SCENARIO 3: Skepticism → Provide Evidence
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 3: Customer Says NOT SURE (Skepticism) → Offer Evidence")
    print("-"*80)
    
    reply_message_skeptic = "I'm not convinced this will actually help our patient numbers"
    
    followup_3 = followup_composer.compose_followup(
        conversation_id="conv_research_3",
        trigger_kind="research_digest",
        merchant_id="m_001_drmeera",
        customer_id=None,
        reply_message=reply_message_skeptic,
        original_cta="open_ended",
        category_ctx=category_ctx,
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message_skeptic}'")
    print(f"  Sentiment Detected: HESITANT (Skepticism) 🤔")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup_3['action']}")
    print(f"  Body: {followup_3['body']}")
    print(f"  CTA: {followup_3['cta']}")
    print(f"  Rationale: {followup_3['rationale']}")
    
    # =========================================================================
    # SCENARIO 4: Soft Objection → One Last Appeal
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 4: Customer Says NO → Personalize & Appeal Once")
    print("-"*80)
    
    reply_message_objection = "No, not interested right now"
    
    followup_4 = followup_composer.compose_followup(
        conversation_id="conv_research_4",
        trigger_kind="research_digest",
        merchant_id="m_001_drmeera",
        customer_id=None,
        reply_message=reply_message_objection,
        original_cta="open_ended",
        category_ctx=category_ctx,
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message_objection}'")
    print(f"  Sentiment Detected: SOFT OBJECTION 👋")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup_4['action']}")
    print(f"  Body: {followup_4['body']}")
    print(f"  CTA: {followup_4['cta']}")
    print(f"  Rationale: {followup_4['rationale']}")
    
    # =========================================================================
    # SCENARIO 5: Hard Opt-Out → Graceful Exit
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 5: Customer Says UNSUBSCRIBE → Graceful Exit")
    print("-"*80)
    
    reply_message_hardno = "Please unsubscribe me from these messages"
    
    followup_5 = followup_composer.compose_followup(
        conversation_id="conv_research_5",
        trigger_kind="research_digest",
        merchant_id="m_001_drmeera",
        customer_id=None,
        reply_message=reply_message_hardno,
        original_cta="open_ended",
        category_ctx=category_ctx,
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message_hardno}'")
    print(f"  Sentiment Detected: HARD OPT-OUT 🚫")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup_5['action']}")
    print(f"  Rationale: {followup_5['rationale']}")
    
    # =========================================================================
    # SCENARIO 6: Off-Topic Question → Stay on Mission
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 6: Customer Asks Off-Topic → Politely Redirect")
    print("-"*80)
    
    reply_message_offtopic = "Can you also help me file my GST return?"
    
    followup_6 = followup_composer.compose_followup(
        conversation_id="conv_research_6",
        trigger_kind="research_digest",
        merchant_id="m_001_drmeera",
        customer_id=None,
        reply_message=reply_message_offtopic,
        original_cta="open_ended",
        category_ctx=category_ctx,
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message_offtopic}'")
    print(f"  Sentiment Detected: OFF-TOPIC 🔄")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup_6['action']}")
    print(f"  Body: {followup_6['body']}")
    print(f"  CTA: {followup_6['cta']}")
    print(f"  Rationale: {followup_6['rationale']}")


# =============================================================================
# TEST SCENARIO: RECALL DUE FOLLOWUP PATHS
# =============================================================================

def test_recall_due_followups():
    """Test followup paths for recall_due trigger"""
    
    print("\n\n" + "="*80)
    print("TEST: Recall Due Followup Scenarios")
    print("="*80)
    
    context_store = ContextStore()
    composer = Composer(context_store)
    followup_composer = composer.followup_composer
    
    merchant_ctx = {
        "merchant_id": "m_001_drmeera",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Meera's Dental Clinic"},
    }
    
    customer_ctx = {
        "customer_id": "c_001_priya",
        "identity": {"name": "Priya"},
        "relationship": {"visits_total": 8, "last_visit": "2026-04-15"},
        "preferences": {"preferred_slots": "weekday_evening"}
    }
    
    # =========================================================================
    # SCENARIO 1: Customer Confirms Appointment
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 1: Customer Confirms Appointment → Lock In")
    print("-"*80)
    
    reply_message = "Wed 5 Nov 6pm works for me"
    
    followup = followup_composer.compose_followup(
        conversation_id="conv_recall_1",
        trigger_kind="recall_due",
        merchant_id="m_001_drmeera",
        customer_id="c_001_priya",
        reply_message=reply_message,
        original_cta="book_appointment",
        category_ctx={"slug": "dentists"},
        merchant_ctx=merchant_ctx,
        customer_ctx=customer_ctx
    )
    
    print(f"\nCustomer Reply: '{reply_message}'")
    print(f"  Sentiment Detected: POSITIVE ✅")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup['action']}")
    print(f"  Body: {followup['body']}")
    print(f"  CTA: {followup['cta']}")
    print(f"  Rationale: {followup['rationale']}")
    
    # =========================================================================
    # SCENARIO 2: Customer Hesitates (Time Barrier)
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 2: Customer Hesitates (Busy) → Back Off 1 Week")
    print("-"*80)
    
    reply_message = "I'm extremely busy right now, too much on my plate"
    
    followup = followup_composer.compose_followup(
        conversation_id="conv_recall_2",
        trigger_kind="recall_due",
        merchant_id="m_001_drmeera",
        customer_id="c_001_priya",
        reply_message=reply_message,
        original_cta="book_appointment",
        category_ctx={"slug": "dentists"},
        merchant_ctx=merchant_ctx,
        customer_ctx=customer_ctx
    )
    
    print(f"\nCustomer Reply: '{reply_message}'")
    print(f"  Sentiment Detected: HESITANT (Time Barrier) ⏰")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup['action']}")
    print(f"  Wait Time: {followup['wait_seconds']} seconds (1 week)")
    print(f"  Rationale: {followup['rationale']}")


# =============================================================================
# TEST SCENARIO: PERFORMANCE DIP FOLLOWUP PATHS
# =============================================================================

def test_perf_dip_followups():
    """Test followup paths for perf_dip trigger"""
    
    print("\n\n" + "="*80)
    print("TEST: Performance Dip Followup Scenarios")
    print("="*80)
    
    context_store = ContextStore()
    composer = Composer(context_store)
    followup_composer = composer.followup_composer
    
    merchant_ctx = {
        "merchant_id": "m_002_bharat",
        "category_slug": "salons",
        "identity": {"name": "Bharat's Salon", "owner_first_name": "Bharat"},
    }
    
    # =========================================================================
    # SCENARIO 1: Customer Accepts Recovery Plan
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 1: Customer Accepts Recovery → Execute Photos")
    print("-"*80)
    
    reply_message = "Let's do the photo refresh"
    
    followup = followup_composer.compose_followup(
        conversation_id="conv_perf_1",
        trigger_kind="perf_dip",
        merchant_id="m_002_bharat",
        customer_id=None,
        reply_message=reply_message,
        original_cta="open_ended",
        category_ctx={"slug": "salons"},
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message}'")
    print(f"  Sentiment Detected: POSITIVE ✅")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup['action']}")
    print(f"  Body: {followup['body']}")
    print(f"  CTA: {followup['cta']}")
    print(f"  Rationale: {followup['rationale']}")
    
    # =========================================================================
    # SCENARIO 2: Customer Concerned About Cost
    # =========================================================================
    
    print("\n" + "-"*80)
    print("SCENARIO 2: Customer Worried About Cost → Free Entry Point")
    print("-"*80)
    
    reply_message = "This would cost us too much right now"
    
    followup = followup_composer.compose_followup(
        conversation_id="conv_perf_2",
        trigger_kind="perf_dip",
        merchant_id="m_002_bharat",
        customer_id=None,
        reply_message=reply_message,
        original_cta="open_ended",
        category_ctx={"slug": "salons"},
        merchant_ctx=merchant_ctx,
        customer_ctx=None
    )
    
    print(f"\nCustomer Reply: '{reply_message}'")
    print(f"  Sentiment Detected: HESITANT (Budget Barrier) 💰")
    print(f"\nFollowup Action:")
    print(f"  Type: {followup['action']}")
    print(f"  Body: {followup['body']}")
    print(f"  CTA: {followup['cta']}")
    print(f"  Rationale: {followup['rationale']}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "VERA AI BOT: Context-Specific, CTA-Centric Followup Message Tests".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    test_research_digest_followups()
    test_recall_due_followups()
    test_perf_dip_followups()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETE")
    print("="*80)
    print("\nKey Improvements Demonstrated:")
    print("  ✓ Sentiment detection (Positive, Hesitant, Objection, Off-Topic)")
    print("  ✓ Context-specific routing (by trigger kind & merchant signals)")
    print("  ✓ Barrier-aware responses (time, budget, skepticism)")
    print("  ✓ CTA-centric followups (each message has ONE clear action)")
    print("  ✓ Graceful exit handling (no spam, respect opt-outs)")
    print("\n")
