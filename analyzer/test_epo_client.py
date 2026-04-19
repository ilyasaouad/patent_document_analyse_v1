"""Quick test for the EPO client and Phase 1 prompt parsing."""
import sys
from pathlib import Path

# Mirror the path setup from the app
_THIS_DIR = Path(__file__).resolve().parent / "search_strategy_analyse"
sys.path.insert(0, str(_THIS_DIR))

from search_utils.epo_client import EPOClassificationClient
from search_config.search_prompts import parse_phase1_classes

print("=" * 60)
print("TEST 1: EPO API — Fetch G06 hierarchy")
print("=" * 60)

client = EPOClassificationClient(max_depth=2)
node = client.fetch_hierarchy("G06")

if node:
    print(f"Root: {node.symbol} — {node.title}")
    print(f"Children: {len(node.children)}")
    print()
    print(node.to_tree_string())
else:
    print("FAILED: Could not fetch G06")

print()
print("=" * 60)
print("TEST 2: Build enriched hints for [G06, H03]")
print("=" * 60)

hints = client.build_enriched_hints(["G06", "H03"])
# Just show the first 1000 chars
print(hints[:1000])
print(f"... ({len(hints)} chars total)")

print()
print("=" * 60)
print("TEST 3: Parse Phase 1 LLM responses")
print("=" * 60)

# Test various response formats
test_cases = [
    ("Plain lines", "G06\nH03\nH04"),
    ("Code block", "```\nG06\nH03\nA61\n```"),
    ("With descriptions", "G06 — Computing\nH03 — Electronic circuitry\nA61 — Medical"),
    ("Comma-separated", "G06, H03, H04, A61"),
    ("Messy format", "Based on analysis:\n```\nG06\nH04\n```\nThese are the most relevant."),
]

for name, response in test_cases:
    result = parse_phase1_classes(response)
    print(f"  {name:25s} → {result}")

print()
print("All tests completed!")
