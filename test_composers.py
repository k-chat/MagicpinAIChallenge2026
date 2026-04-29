#!/usr/bin/env python3
"""
Test script: Load dataset and test real composers
"""

import json
import requests
from pathlib import Path
from datetime import datetime

BOT_URL = "http://localhost:8080"
DATASET_DIR = Path(__file__).parent / "dataset"

def load_json(path):
    with open(path) as f:
        return json.load(f)

print("\n" + "="*70)
print("VERA BOT — COMPOSER TEST")
print("="*70)

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

# Push context to bot
print("\n[2] Pushing context to bot...")

# Categories
for slug, cat in categories.items():
    payload = {
        "scope": "category",
        "context_id": slug,
        "version": 1,
        "payload": cat,
        "delivered_at": "2026-04-26T10:00:00Z"
    }
    r = requests.post(f"{BOT_URL}/v1/context", json=payload)
    assert r.status_code == 200, f"Failed to push category {slug}"
print(f"  ✓ {len(categories)} categories")

# Merchants
for merchant in merchants_data["merchants"]:
    payload = {
        "scope": "merchant",
        "context_id": merchant["merchant_id"],
        "version": 1,
        "payload": merchant,
        "delivered_at": "2026-04-26T10:00:00Z"
    }
    r = requests.post(f"{BOT_URL}/v1/context", json=payload)
    assert r.status_code == 200, f"Failed to push merchant {merchant['merchant_id']}"
print(f"  ✓ {len(merchants_data['merchants'])} merchants")

# Customers
for customer in customers_data["customers"]:
    payload = {
        "scope": "customer",
        "context_id": customer["customer_id"],
        "version": 1,
        "payload": customer,
        "delivered_at": "2026-04-26T10:00:00Z"
    }
    r = requests.post(f"{BOT_URL}/v1/context", json=payload)
    assert r.status_code == 200, f"Failed to push customer {customer['customer_id']}"
print(f"  ✓ {len(customers_data['customers'])} customers")

# Triggers
for trigger in triggers_data["triggers"]:
    payload = {
        "scope": "trigger",
        "context_id": trigger["id"],
        "version": 1,
        "payload": trigger,
        "delivered_at": "2026-04-26T10:00:00Z"
    }
    r = requests.post(f"{BOT_URL}/v1/context", json=payload)
    assert r.status_code == 200, f"Failed to push trigger {trigger['id']}"
print(f"  ✓ {len(triggers_data['triggers'])} triggers")

# Test tick with specific triggers
print("\n[3] Testing composers...")

# Find triggers by kind
research_triggers = [t for t in triggers_data["triggers"] if t["kind"] == "research_digest"][:1]
recall_triggers = [t for t in triggers_data["triggers"] if t["kind"] == "recall_due"][:1]
perf_triggers = [t for t in triggers_data["triggers"] if t["kind"] == "perf_dip"][:1]

test_triggers = research_triggers + recall_triggers + perf_triggers

print(f"\n  Testing {len(test_triggers)} trigger types:")

for trigger in test_triggers:
    trigger_id = trigger["id"]
    trigger_kind = trigger["kind"]
    
    payload = {
        "now": "2026-04-26T10:30:00Z",
        "available_triggers": [trigger_id]
    }
    
    r = requests.post(f"{BOT_URL}/v1/tick", json=payload)
    result = r.json()
    
    actions = result.get("actions", [])
    if actions:
        action = actions[0]
        print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  Trigger: {trigger_kind.upper()}")
        print(f"  Merchant: {action['merchant_id']}")
        if action.get('customer_id'):
            print(f"  Customer: {action['customer_id']}")
        print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"\n  Message:\n    {action['body']}")
        print(f"\n  Metadata:")
        print(f"    CTA: {action['cta']}")
        print(f"    Send as: {action['send_as']}")
        print(f"    Suppression key: {action['suppression_key']}")
        print(f"    Rationale: {action['rationale']}")
    else:
        print(f"\n  ✗ {trigger_kind}: No action composed")

# Check state
print("\n[4] Final state:")
r = requests.get(f"{BOT_URL}/v1/state")
state = r.json()
print(f"  Categories: {state['contexts_loaded']['category']}")
print(f"  Merchants: {state['contexts_loaded']['merchant']}")
print(f"  Customers: {state['contexts_loaded']['customer']}")
print(f"  Triggers: {state['contexts_loaded']['trigger']}")
print(f"  Conversations: {state['conversations_total']}")

print("\n" + "="*70)
print("✓ All tests complete!")
print("="*70 + "\n")
