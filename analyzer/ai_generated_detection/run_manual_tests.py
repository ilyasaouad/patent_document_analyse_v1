import os
import sys

# Ensure we can import the submodules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.helpers import truncate_text, parse_json_safe, extract_figure_references
from config.settings import AnalyzerConfig
from core.models import PatentDocument, DetectionResult
from core.ollama_client import OllamaClient

def run_tests():
    print("="*50)
    print("🚨 AI PATENT ANALYZER - MANUAL TEST SUITE 🚨")
    print("="*50)

    # ---------------------------------------------------------
    # 1. TEST UTILS
    # ---------------------------------------------------------
    print("\n[1] Testing utils/helpers.py...")
    try:
        text = "This is a very long patent description."
        truncated = truncate_text(text, 15)
        print(f"  ✓ truncate_text: '{text}' -> '{truncated}'")
        
        json_str = 'Here is the response: ```json\n{"score": 0.8, "findings": ["AI"]}\n```'
        parsed = parse_json_safe(json_str, fallback={})
        print(f"  ✓ parse_json_safe: successfully extracted {parsed}")

        refs = extract_figure_references("As shown in Figure 2 and FIG. 3A.")
        print(f"  ✓ extract_figure_references: found {refs}")
    except Exception as e:
        print(f"  ❌ Error in utils: {e}")

    # ---------------------------------------------------------
    # 2. TEST CONFIG
    # ---------------------------------------------------------
    print("\n[2] Testing config/settings.py...")
    try:
        config = AnalyzerConfig()
        is_valid = config.validate()
        print(f"  ✓ Default Config Loaded. AI_DETECTION_THRESHOLD = {config.AI_DETECTION_THRESHOLD}")
        print(f"  ✓ Config Validation: {'PASSED' if is_valid else 'FAILED'}")
    except Exception as e:
        print(f"  ❌ Error in config: {e}")

    # ---------------------------------------------------------
    # 3. TEST MODELS
    # ---------------------------------------------------------
    print("\n[3] Testing core/models.py...")
    try:
        doc = PatentDocument("test.md", "/fake/path/test.md", "Content...", "description")
        print(f"  ✓ PatentDocument created: {doc.file_name} ({doc.doc_type})")

        res = DetectionResult(
            is_likely_ai_generated=True,
            confidence_score=0.85,
            risk_level="HIGH",
            feature_scores={"fingerprint": 0.8},
            detailed_analysis={},
            recommendations=["Review manually!"],
            applied_rules=[],
            metadata={}
        )
        print(f"  ✓ DetectionResult created. Risk Level: {res.risk_level}")
    except Exception as e:
        print(f"  ❌ Error in models: {e}")

    # ---------------------------------------------------------
    # 4. TEST OLLAMA CLIENT
    # ---------------------------------------------------------
    print("\n[4] Testing core/ollama_client.py...")
    try:
        client = OllamaClient(model_name=config.OLLAMA_MODEL, base_url=config.OLLAMA_URL)
        print(f"  -> Attempting to connect to Ollama at {config.OLLAMA_URL}")
        
        models = client.get_available_models()
        if models:
            print(f"  ✓ Connection successful! Found {len(models)} models.")
            print(f"  ✓ Top 3 available models: {models[:3]}")
            
            # Check if our requested model is actually installed
            if any(config.OLLAMA_MODEL in m for m in models):
                print(f"  ✓ Requested model '{config.OLLAMA_MODEL}' IS installed.")
            else:
                print(f"  ⚠️ Warning: Model '{config.OLLAMA_MODEL}' NOT found in Ollama.")
        else:
            print(f"  ❌ Could not retrieve models. Is Ollama running?")
            print(f"     Try running: ollama serve")
    except Exception as e:
        print(f"  ❌ Error testing Ollama: {e}")

    print("\n" + "="*50)
    print("DONE with manual tests.")
    print("="*50)

if __name__ == "__main__":
    run_tests()
