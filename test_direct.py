#!/usr/bin/env python3
"""
Direct composer test — imports bot.py and tests composers with sample data
"""

import json
from pathlib import Path
from bot import Composer, ContextStore

DATASET_DIR = Path(__file__).parent / "dataset"

def load_json(path):
    with open(path) as f:
        return json.load(f)

print("\n" + "="*80)
print("VERA BOT — DIRECT COMPOSER TEST")
print("="*80)

# Load dataset
print("\n[1] Loading dataset...")
categories = {}
for cat_file in (DATASET_DIR / "categories").glob("*.json"):
    cat = load_json(cat_file)
    categories[cat["slug"]] = cat
    print(f"  ✓ {cat['slug']}")

merchants_data = load_json(DATASET_DIR / "merchants_seed.json")
customers_data = load_json(DATASET_DIR / "customers_seed.json")
triggers_data = load_json(DATASET_DIR / "triggers_seed.json")

print(f"  ✓ {len(merchants_data['merchants'])} merchants")
print(f"  ✓ {len(customers_data['customers'])} customers")
print(f"  ✓ {len(triggers_data['triggers'])} triggers")

# Create composer
print("\n[2] Initializing composer...")
store = ContextStore()
composer = Composer(store)
print("  ✓ Composer ready")

# Test each trigger type
print("\n[3] Testing composer methods...")

# Find test triggers
research_trigger = next((t for t in triggers_data["triggers"] if t["kind"] == "research_digest"), None)
recall_trigger = next((t for t in triggers_data["triggers"] if t["kind"] == "recall_due"), None)
perf_trigger = next((t for t in triggers_data["triggers"] if t["kind"] == "perf_dip"), None)

test_cases = [
    ("research_digest", research_trigger),
    ("recall_due", recall_trigger),
    ("perf_dip", perf_trigger),
]

for trigger_name, trigger_ctx in test_cases:
    if not trigger_ctx:
        print(f"\n  ✗ {trigger_name}: No trigger found")
        continue
    
    # Get merchant
    merchant_id = trigger_ctx.get("merchant_id")
    merchant_ctx = next((m for m in merchants_data["merchants"] if m["merchant_id"] == merchant_id), None)
    
    if not merchant_ctx:
        print(f"\n  ✗ {trigger_name}: Merchant not found")
        continue
    
    # Get category
    category_slug = merchant_ctx.get("category_slug")
    category_ctx = categories.get(category_slug)
    
    if not category_ctx:
        print(f"\n  ✗ {trigger_name}: Category not found")
        continue
    
    # Get customer if needed
    customer_ctx = None
    customer_id = trigger_ctx.get("customer_id")
    if customer_id:
        customer_ctx = next((c for c in customers_data["customers"] if c["customer_id"] == customer_id), None)
    
    # Compose
    try:
        result = composer.compose(
            category_ctx=category_ctx,
            merchant_ctx=merchant_ctx,
            trigger_ctx=trigger_ctx,
            customer_ctx=customer_ctx
        )
        
        print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  {trigger_name.upper()}")
        print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"\n  Merchant: {merchant_id}")
        if customer_id:
            print(f"  Customer: {customer_id}")
        
        print(f"\n  📨 Message:")
        print(f"     {result.body}")
        
        print(f"\n  Metadata:")
        print(f"     CTA: {result.cta}")
        print(f"     Send as: {result.send_as}")
        print(f"     Suppression key: {result.suppression_key}")
        
        print(f"\n  Scores:")
        scores = result.scores or {}
        for dim, score in scores.items():
            bar = "█" * score + "░" * (10 - score)
            print(f"     {dim:20} [{bar}] {score}/10")
        
        print(f"\n  Rationale:")
        print(f"     {result.rationale}")
        
    except Exception as e:
        print(f"\n  ✗ {trigger_name}: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("✓ Composer tests complete!")
print("="*80 + "\n")
