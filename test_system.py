import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import init_db
from modules.orchestrator import PixelWiseOrchestrator
from modules.classifier import RequestClassifier
from modules.cost_router import CostRouter
from modules.zero_ai_library import ZeroAILibrary
from modules.verifier import QualityVerifier

def test_pipeline():
    init_db()
    print("=== Testing PixelWise AI Decision Engine ===")

    # Test 1: Elephant coloring worksheet (Should route to Zero-AI SVG or Reuse at ₹0 or ₹0.05)
    prompt1 = "Create an elephant colouring worksheet for a seven-year-old with thick outlines"
    print(f"\n[Test 1] Prompt: '{prompt1}'")
    res1 = PixelWiseOrchestrator.execute_request("SCH-001", "Mrs. Sharma", prompt1, "worksheet", "kindergarten")
    print(f" -> Chosen Tier: {res1['routing']['chosen_tier']} ({res1['routing']['tier_name']})")
    print(f" -> Actual Cost: ₹{res1['actual_cost']} (Baseline: ₹{res1['baseline_cost']}) -> Saved: ₹{res1['cost_saved']} ({res1['savings_pct']}%)")
    print(f" -> Final Status: {res1['final_status']}")
    assert res1['actual_cost'] <= 0.10, "Coloring sheet should be Zero-AI or Reused at negligible cost!"

    # Test 2: Butterfly coloring page (Should match shared library cache at ₹0.00)
    prompt2 = "Monarch butterfly outline coloring page with symmetrical wings"
    print(f"\n[Test 2] Prompt: '{prompt2}'")
    res2 = PixelWiseOrchestrator.execute_request("SCH-002", "Mr. Davis", prompt2, "worksheet", "primary")
    print(f" -> Chosen Tier: {res2['routing']['chosen_tier']}")
    print(f" -> Actual Cost: ₹{res2['actual_cost']} -> Saved: ₹{res2['cost_saved']} ({res2['savings_pct']}%)")
    print(f" -> Final Status: {res2['final_status']}")

    # Test 3: Water cycle educational flashcard
    prompt3 = "Water cycle educational diagram showing evaporation and condensation"
    print(f"\n[Test 3] Prompt: '{prompt3}'")
    res3 = PixelWiseOrchestrator.execute_request("SCH-003", "Ms. Garcia", prompt3, "flashcard", "primary")
    print(f" -> Chosen Tier: {res3['routing']['chosen_tier']}")
    print(f" -> Actual Cost: ₹{res3['actual_cost']} -> Saved: ₹{res3['cost_saved']}")

    # Test 4: Annual report poster (Should route to Advanced AI because complexity is 5)
    prompt4 = "District Annual Report high-resolution commemorative poster"
    print(f"\n[Test 4] Prompt: '{prompt4}'")
    res4 = PixelWiseOrchestrator.execute_request("SCH-004", "Dr. Rao", prompt4, "poster", "high")
    print(f" -> Chosen Tier: {res4['routing']['chosen_tier']}")
    print(f" -> Actual Cost: ₹{res4['actual_cost']} -> Saved: ₹{res4['cost_saved']}")

    # Test 5: Defect auto-correction test
    print(f"\n[Test 5] Defect Auto-Correction Test (Simulated muddy gray background)")
    res5 = PixelWiseOrchestrator.execute_request("SCH-005", "Mrs. Wilson", "Cartoon puppy line art to color", "worksheet", "primary", force_defect=True)
    print(f" -> Chosen Tier: {res5['routing']['chosen_tier']}")
    print(f" -> Final Status: {res5['final_status']}")
    print(f" -> Attempts: {len(res5['attempts_log'])}")
    for a in res5['attempts_log']:
        print(f"    - Attempt {a['attempt']}: {a['action']} -> Result: {a['status']} (Cost: ₹{a['total_attempt_cost']})")

    print("\n All pipeline tests completed successfully!")

if __name__ == "__main__":
    test_pipeline()
