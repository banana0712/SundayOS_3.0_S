#!/usr/bin/env python3
"""Test script for context window compression observability."""
import requests
import json
import time

BASE_URL = "http://localhost:8001"
HEADERS = {
    "Content-Type": "application/json",
    "X-Sunday-Token": "dev-key"
}

def test_compression_observability():
    """Test compression metrics and history endpoints."""
    print("=" * 70)
    print("Context Window Compression Observability Test")
    print("=" * 70)

    # Step 1: Create a new conversation
    print("\n[1] Creating conversation...")
    resp = requests.post(
        f"{BASE_URL}/api/conversations",
        headers=HEADERS,
        json={"title": "Observability Test"},
        timeout=10
    )
    conv_id = resp.json()["id"]
    print(f"    Created: {conv_id}")

    # Step 2: Send 15 messages to trigger compression
    print("\n[2] Sending 15 messages to trigger compression...")
    for i in range(1, 16):
        resp = requests.post(
            f"{BASE_URL}/api/chat",
            headers=HEADERS,
            json={
                "message": f"This is test message number {i}. I'm testing the compression system.",
                "conversation_id": conv_id
            },
            timeout=60
        )
        if resp.status_code == 200:
            print(f"    [OK] Message {i}")
        else:
            print(f"    [FAIL] Message {i}: {resp.status_code}")
            return

    # Step 3: Check global compression stats
    print("\n[3] Checking global compression statistics...")
    resp = requests.get(
        f"{BASE_URL}/api/debug/compression-stats",
        headers=HEADERS,
        timeout=10
    )

    if resp.status_code == 200:
        stats = resp.json()["stats"]
        print(f"    Total conversations compressed: {stats.get('total_conversations_compressed', 0)}")
        print(f"    Total compressions: {stats.get('total_compressions', 0)}")
        print(f"    Average compression ratio: {stats.get('avg_compression_ratio', 0):.2f}x")
        print(f"    Average time: {stats.get('avg_time_ms', 0):.0f}ms")
        print(f"    Total facts extracted: {stats.get('total_facts_extracted', 0)}")
        print(f"    Total messages compressed: {stats.get('total_messages_compressed', 0)}")
    else:
        print(f"    [FAIL] Could not fetch stats: {resp.status_code}")

    # Step 4: Check conversation-specific compression history
    print(f"\n[4] Checking compression history for conversation {conv_id}...")
    resp = requests.get(
        f"{BASE_URL}/api/debug/compression-history/{conv_id}",
        headers=HEADERS,
        timeout=10
    )

    if resp.status_code == 200:
        data = resp.json()["data"]
        stats = data["stats"]
        history = data["history"]

        print(f"\n    Conversation Stats:")
        print(f"      Total compressions: {stats.get('total_compressions', 0)}")
        print(f"      Average compression ratio: {stats.get('avg_compression_ratio', 0):.2f}x")
        print(f"      Average time: {stats.get('avg_time_ms', 0):.0f}ms")
        print(f"      Total facts extracted: {stats.get('total_facts_extracted', 0)}")
        print(f"      Average token savings: {stats.get('avg_token_savings_percent', 0):.1f}%")

        print(f"\n    Compression History ({len(history)} records):")
        for i, record in enumerate(history, 1):
            print(f"\n      [{i}] {record['timestamp']}")
            print(f"          Messages: {record['original_message_count']} → {record['kept_message_count']} kept")
            print(f"          Compressed: {record['compressed_message_count']} messages")
            print(f"          Ratio: {record['compression_ratio']}x")
            print(f"          Time: {record['compression_time_ms']:.0f}ms")
            print(f"          Summary length: {record['summary_length']} chars")
            print(f"          Facts extracted: {record['facts_extracted_count']}")
            print(f"          Token savings: {record['token_savings']} ({record['token_savings_percent']}%)")
    else:
        print(f"    [FAIL] Could not fetch history: {resp.status_code}")

    # Step 5: Verify conversation state
    print(f"\n[5] Verifying conversation state...")
    resp = requests.get(
        f"{BASE_URL}/api/conversations/{conv_id}",
        headers=HEADERS,
        timeout=10
    )

    if resp.status_code == 200:
        conv = resp.json()
        print(f"    Total messages in conversation: {len(conv['messages'])}")
        print(f"    (Should be less than 15 due to compression)")

    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_compression_observability()
