#!/usr/bin/env python3
"""
Quick test script to load dataset and test bot endpoints
"""

import json
import requests
from pathlib import Path

BOT_URL = "http://localhost:8080"
DATASET_DIR = Path(__file__).parent / "dataset"

def load_json(path):
    with open(path) as f:
        return json.load(f)

def test_context_push():
    """Load and push dataset contexts to bot"""
    print("\n=== Testing Context Push ===\n")
    
    # Load categories
    category_files = list((DATASET_DIR / "categories").glob("*.json"))
    for cat_file in category_files:
        category = load_json(cat_file)
        slug = category["slug"]
        
        payload = {
            "scope": "category",
            "context_id": slug,
            "version": 1,
            "payload": category,
            "delivered_at": "2026-04-26T10:00:00Z"
        }
        
        resp = requests.post(f"{BOT_URL}/v1/context", json=payload)
        print(f"Category {slug}: {resp.status_code} - {resp.json()}")
    
    # Load merchants
    merchants_data = load_json(DATASET_DIR / "merchants_seed.json")
    for merchant in merchants_data["merchants"]:
        merchant_id = merchant["merchant_id"]
        
        payload = {
            "scope": "merchant",
            "context_id": merchant_id,
            "version": 1,
            "payload": merchant,
            "delivered_at": "2026-04-26T10:00:00Z"
        }
        
        resp = requests.post(f"{BOT_URL}/v1/context", json=payload)
        print(f"Merchant {merchant_id}: {resp.status_code}")
    
    # Load customers
    customers_data = load_json(DATASET_DIR / "customers_seed.json")
    for customer in customers_data["customers"]:
        customer_id = customer["customer_id"]
        
        payload = {
            "scope": "customer",
            "context_id": customer_id,
            "version": 1,
            "payload": customer,
            "delivered_at": "2026-04-26T10:00:00Z"
        }
        
        resp = requests.post(f"{BOT_URL}/v1/context", json=payload)
        print(f"Customer {customer_id}: {resp.status_code}")
    
    # Load triggers
    triggers_data = load_json(DATASET_DIR / "triggers_seed.json")
    for trigger in triggers_data["triggers"]:
        trigger_id = trigger["id"]
        
        payload = {
            "scope": "trigger",
            "context_id": trigger_id,
            "version": 1,
            "payload": trigger,
            "delivered_at": "2026-04-26T10:00:00Z"
        }
        
        resp = requests.post(f"{BOT_URL}/v1/context", json=payload)
        print(f"Trigger {trigger_id}: {resp.status_code}")

def test_tick():
    """Test /v1/tick endpoint"""
    print("\n=== Testing Tick Endpoint ===\n")
    
    triggers_data = load_json(DATASET_DIR / "triggers_seed.json")
    trigger_ids = [t["id"] for t in triggers_data["triggers"][:3]]
    
    payload = {
        "now": "2026-04-26T10:30:00Z",
        "available_triggers": trigger_ids
    }
    
    resp = requests.post(f"{BOT_URL}/v1/tick", json=payload)
    result = resp.json()
    
    print(f"Status: {resp.status_code}")
    print(f"Actions composed: {len(result.get('actions', []))}")
    
    for action in result.get("actions", []):
        print(f"\n  Conversation: {action['conversation_id']}")
        print(f"  Merchant: {action['merchant_id']}")
        print(f"  Body: {action['body']}")
        print(f"  CTA: {action['cta']}")
        print(f"  Rationale: {action['rationale']}")

def test_state():
    """Test /v1/state endpoint"""
    print("\n=== Testing State Endpoint ===\n")
    
    resp = requests.get(f"{BOT_URL}/v1/state")
    result = resp.json()
    
    print(f"Status: {resp.status_code}")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_context_push()
    test_tick()
    test_state()
    print("\n✓ All tests complete!")
