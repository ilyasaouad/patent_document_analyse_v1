"""
ai_detect_analyse.py
===================
AI detection analyzer for patent markdown files.
LOCAL-ONLY version using Ollama (100% privacy-focused).
"""

import os
import glob
import json
import requests
import sys
from pathlib import Path
from typing import Dict, List, Any

# Map to the project root to import central config
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from config.settings import settings
except ImportError:
    print("Warning: Could not load global settings.py. Reverting to hardcoded local defaults.")
    class DefaultSettings:
        OLLAMA_URL = "http://localhost:11434"
        OLLAMA_MODEL = "gpt-oss:120b-cloud"
        AI_DETECTION_THRESHOLD = 0.6
        LLM_API_KEY = ""
    settings = DefaultSettings()

class ai_detect_analyse:
    """
    Analyzes patent markdown files for AI-generated content.
    Uses LOCAL Ollama only - 100% private, no cloud services.
    """
    
    def __init__(
        self, 
        input_dir: str,
        ollama_model: str = None,
        detection_threshold: float = None,
        ollama_url: str = None,
        api_key: str = None
    ):
        """
        Initialize the analyzer with the directory containing output documents.
        
        Args:
            input_dir: Directory containing markdown files
            ollama_model: Ollama model name (default: from settings.py)
            detection_threshold: AI classification threshold (default: from settings.py)
            ollama_url: Ollama API endpoint (default: from settings.py)
            api_key: Optional API key for remote providers (default: from settings.py)
        """
        self.input_dir = input_dir
        self.documents = []
        
        # Load exactly from kwargs, but fallback natively to the global configuration file
        self.ollama_model = ollama_model if ollama_model is not None else settings.OLLAMA_MODEL
        self.detection_threshold = detection_threshold if detection_threshold is not None else settings.AI_DETECTION_THRESHOLD
        self.ollama_url = ollama_url if ollama_url is not None else settings.OLLAMA_URL
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        
        # Storage for categorized content
        self.description_text = ""
        self.claims_text = ""
        self.drawings_text = ""
        
        # Test Ollama connection
        self._test_ollama_connection()
        
        # Load documents
        self._load_documents()
    
    def _test_ollama_connection(self):
        """Test connection to local Ollama instance."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                print(f"✓ Connected to Ollama at {self.ollama_url}")
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                # Check if requested model is available
                available = False
                for name in model_names:
                    if name.startswith(self.ollama_model):
                        available = True
                        break
                
                if not available:
                    print(f"⚠️ Model '{self.ollama_model}' not found.")
                    if model_names:
                        print(f"   Available models: {', '.join(model_names[:3])}")
                    print(f"   Pull with: ollama pull {self.ollama_model}")
                else:
                    print(f"✓ Model '{self.ollama_model}' is available")
            else:
                print(f"⚠️ Ollama responded with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to Ollama at {self.ollama_url}")
            print(f"   Make sure Ollama is running: ollama serve")
            raise ConnectionError(f"Ollama not available: {e}")
    
    def _load_documents(self):
        """
        Loads all markdown files from the specified input directory.
        Finds all readied md files (like description_only.md, claims_from_description.md, etc.)
        """
        if not os.path.isdir(self.input_dir):
            print(f"Error: Directory '{self.input_dir}' does not exist.")
            return

        # Search for all markdown files in the input directory
        search_pattern = os.path.join(self.input_dir, "*.md")
        md_files = glob.glob(search_pattern)
        
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_name = os.path.basename(file_path).lower()
                    
                    self.documents.append({
                        "file_name": os.path.basename(file_path),
                        "file_path": file_path,
                        "content": content
                    })
                    
                    # Categorize by strictly checking if the filename STARTS with the target word
                    if file_name.startswith("claim"):
                        self.claims_text = content
                        print(f"✓ Loaded claims: {os.path.basename(file_path)}")
                    elif file_name.startswith("description") or file_name.startswith("describtion"):
                        self.description_text = content
                        print(f"✓ Loaded description: {os.path.basename(file_path)}")
                    elif file_name.startswith("drawing"):
                        self.drawings_text = content
                        print(f"✓ Loaded drawings: {os.path.basename(file_path)}")
                    else:
                        print(f"✓ Loaded: {os.path.basename(file_path)}")
                        
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        
        print(f"\n📄 Loaded {len(self.documents)} document(s) in total ready for deeper analysis.")
        print(f"   Description: {'Yes' if self.description_text else 'No'}")
        print(f"   Claims: {'Yes' if self.claims_text else 'No'}")
        print(f"   Drawings: {'Yes' if self.drawings_text else 'No'}")

    def run_analysis(self) -> Dict[str, Any]:
        """
        Run deep AI analysis on the loaded documents using LOCAL Ollama.
        
        Returns:
            Complete detection result dictionary
        """
        if not self.documents:
            print("No documents found in input directory to analyze.")
            return {
                "error": "No documents found",
                "is_ai_generated": False,
                "confidence_score": 0.0
            }
        
        print(f"\n{'='*60}")
        print(f"🔍 DEEP AI ANALYSIS - LOCAL MODE (Ollama)")
        print(f"{'='*60}")
        print(f" Total Files: {len(self.documents)}")
        print(f" Model: {self.ollama_model}")
        print(f" Threshold: {self.detection_threshold:.0%}")
        print(f"{'='*60}\n")
        
        # Show file preview (your original debug functionality)
        self._show_document_preview()
        
        # Run LOCAL analysis
        print("📍 Running LOCAL analysis (100% Privacy-focused)")
        print("   Method: Anchor Method + Stylometric Fingerprinting\n")
        
        # Phase 1: Stylometric Fingerprinting (30%)
        print("Step 1/5: Stylometric fingerprinting...")
        fingerprint_score = self._ollama_fingerprint_analysis()
        
        # Phase 2: Anchor Method (40%) - STRONGEST SIGNAL
        print("Step 2/5: Anchor method (self-reflexive comparison)...")
        anchor_similarity = self._ollama_anchor_method()
        
        # Phase 3: Technical Hallucination (20%)
        print("Step 3/5: Checking for technical hallucinations...")
        hallucination_score = self._ollama_hallucination_check()
        
        # Phase 4: Drawing Consistency (10%)
        print("Step 4/5: Analyzing drawing consistency...")
        drawing_score = self._ollama_drawing_consistency()
        
        # Phase 5: Calculate weighted score
        print("Step 5/5: Calculating final confidence...")
        confidence = self._calculate_confidence(
            fingerprint_score,
            anchor_similarity,
            hallucination_score,
            drawing_score
        )
        
        # Build result
        result = {
            "is_ai_generated": confidence >= self.detection_threshold,
            "confidence_score": confidence,
            "risk_level": self._get_risk_level(confidence),
            "analysis_mode": "LOCAL",
            "ollama_model": self.ollama_model,
            "fingerprint_analysis": {
                "score": fingerprint_score.get("score", 0.5),
                "findings": fingerprint_score.get("findings", [])
            },
            "anchor_analysis": {
                "similarity": anchor_similarity.get("similarity", 0.5),
                "findings": anchor_similarity.get("findings", [])
            },
            "hallucination_analysis": {
                "score": hallucination_score.get("score", 0.5),
                "findings": hallucination_score.get("findings", [])
            },
            "drawing_analysis": {
                "score": drawing_score.get("score", 0.5),
                "findings": drawing_score.get("findings", [])
            },
            "recommendations": self._generate_recommendations(
                confidence, fingerprint_score, anchor_similarity, drawing_score
            ),
            "detailed_scores": {
                "fingerprint": fingerprint_score.get("score", 0.5),
                "anchor_similarity": anchor_similarity.get("similarity", 0.5),
                "hallucination": hallucination_score.get("score", 0.5),
                "drawing": drawing_score.get("score", 0.5)
            }
        }
        
        # Print summary
        self._print_summary(result)
        
        # Save results
        self._save_result(result)
        
        return result
    
    def _show_document_preview(self):
        """Show preview of loaded documents (original debug functionality)."""
        print("📋 Document Preview:")
        for idx, doc in enumerate(self.documents, 1):
            file_name = doc['file_name']
            file_len = len(doc['content'])
            
            print(f"\n  {idx}. {file_name}")
            print(f"     Path: {doc['file_path']}")
            print(f"     Size: {file_len:,} characters")
            
            if file_len > 0:
                preview_length = 150
                preview_text = doc['content'][:preview_length].strip().replace('\n', ' ')
                print(f"     Preview: \"{preview_text}...\"")
            else:
                print(f"     ⚠️ FILE IS EMPTY")
        
        print(f"\n{'='*60}\n")
    
    # ========================================================================
    # OLLAMA ANALYSIS METHODS
    # ========================================================================
    
    def _ollama_call(self, prompt: str, system_prompt: str = "") -> str:
        """Make a call to local Ollama API."""
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False
            }
            
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                headers=headers,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                print(f"  ⚠️ Ollama error: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"  ⚠️ Ollama call failed: {e}")
            return ""
    
    def _ollama_fingerprint_analysis(self) -> Dict[str, Any]:
        """
        Phase 1: Stylometric Fingerprinting (30% weight)
        Detects LLM patterns: uniform sentences, burstiness, transitions
        """
        if not self.description_text:
            return {"score": 0.5, "findings": ["No description text available"]}
        
        system_prompt = """Analyze text for LLM stylometric markers. Return JSON only:
{"score": 0.0-1.0, "findings": ["finding1", "finding2", "finding3"]}

Look for:
1. Uniform sentence length (low burstiness)
2. Repetitive transitions ("Furthermore", "Moreover", "Additionally")
3. Lack of technical noise/idiosyncrasies
4. Excessive passive voice and generic terms"""
        
        prompt = f"Analyze this patent description for AI fingerprints:\n\n{self.description_text[:4000]}"
        
        response = self._ollama_call(prompt, system_prompt)
        return self._extract_json_from_response(response, {"score": 0.5, "findings": ["Analysis incomplete"]})
    
    def _ollama_anchor_method(self) -> Dict[str, Any]:
        """
        Phase 2: Anchor Method (40% weight) - STRONGEST SIGNAL
        Self-Reflexive Comparison: AI generates own version, compares with original
        """
        if not self.claims_text or not self.description_text:
            return {"similarity": 0.5, "findings": ["Insufficient text for anchor method"]}
        
        # Step 1: Generate AI's own version from claims
        print("     → Generating AI anchor from claims...")
        gen_system = "You are a patent attorney writing a technical description."
        gen_prompt = f"Based on these patent claims, write a technical summary for a patent description. Use formal, legalistic tone:\n\n{self.claims_text[:2000]}"
        
        ai_anchor = self._ollama_call(gen_prompt, gen_system)
        
        if not ai_anchor or len(ai_anchor) < 50:
            return {"similarity": 0.5, "findings": ["Anchor generation failed"]}
        
        # Step 2: Compare original with AI-generated anchor
        print("     → Comparing original with AI-generated anchor...")
        compare_system = "You are comparing text similarity between two patent descriptions."
        compare_prompt = f"""Compare these two patent descriptions. How similar are they in phrasing and logical flow?

Return ONLY this JSON format:
{{"similarity": <0-100>, "findings": ["similarity point 1", "similarity point 2"]}}

ORIGINAL (user's description):
{self.description_text[:2000]}

AI-GENERATED (anchor):
{ai_anchor[:2000]}"""
        
        response = self._ollama_call(compare_prompt, compare_system)
        result = self._extract_json_from_response(response, {"similarity": 50, "findings": ["Comparison incomplete"]})
        
        # Normalize similarity to 0-1 range
        if "similarity" in result:
            result["similarity"] = result["similarity"] / 100.0
        
        return result
    
    def _ollama_hallucination_check(self) -> Dict[str, Any]:
        """
        Phase 3: Technical Hallucination Detection (20% weight)
        Find terms in description not supported by claims
        """
        if not self.claims_text or not self.description_text:
            return {"score": 0.5, "findings": ["Insufficient text for hallucination check"]}
        
        system_prompt = "You detect unsupported technical claims in patent documents."
        prompt = f"""Find technical terms or concepts in the DESCRIPTION that are NOT supported by the CLAIMS.

Return ONLY this JSON format:
{{"score": <0.0-1.0>, "findings": ["unsupported term/concept 1", "unsupported term/concept 2"]}}

CLAIMS (what should be supported):
{self.claims_text[:2000]}

DESCRIPTION (check for unsupported terms):
{self.description_text[:3000]}"""
        
        response = self._ollama_call(prompt, system_prompt)
        return self._extract_json_from_response(response, {"score": 0.5, "findings": ["Analysis incomplete"]})
    
    def _ollama_drawing_consistency(self) -> Dict[str, Any]:
        """
        Phase 4: Drawing Consistency (10% weight)
        Check if description matches actual drawing text (or claims-description alignment)
        """
        if not self.drawings_text:
            import re
            drawing_patterns = r'(?i)(brief description of the drawings?|accompanying drawings?|referring to figure|shown in fig|figur\s+\d+|fig\.\s*\d+|tegning\s+\d+|vist i figur)'
            
            # If drawings are mentioned in the text but missing, flag it explicitly
            if self.description_text and re.search(drawing_patterns, self.description_text):
                result = self._ollama_claims_description_alignment()
                # Insert a critical human-facing warning
                result.get("findings", []).insert(0, "WARNING: Description explicitly references drawings/figures, but no drawing file was provided for analysis.")
                return result
            else:
                # Fallback: check claims-description alignment if no drawings mentioned
                return self._ollama_claims_description_alignment()
        
        system_prompt = "You detect mismatches between patent descriptions and actual drawing content."
        prompt = f"""Compare the patent description against actual drawing content. Find contradictions or deviations.

Return ONLY this JSON format:
{{"score": <0.0-1.0>, "findings": ["deviation 1", "deviation 2"]}}

DESCRIPTION (what it says about figures):
{self.description_text[:3000]}

ACTUAL DRAWING TEXT (OCR extracted):
{self.drawings_text[:1500]}"""
        
        response = self._ollama_call(prompt, system_prompt)
        return self._extract_json_from_response(response, {"score": 0.5, "findings": ["Analysis incomplete"]})
    
    def _ollama_claims_description_alignment(self) -> Dict[str, Any]:
        """Fallback: Check claims-description alignment if no drawings."""
        system_prompt = "You check patent claim-description alignment for consistency issues."
        prompt = f"""Check alignment between CLAIMS and DESCRIPTION. AI often struggles with maintaining complex antecedent basis across sections.

Return ONLY this JSON format:
{{"score": <0.0-1.0>, "findings": ["misalignment issue 1", "misalignment issue 2"]}}

CLAIMS:
{self.claims_text[:2000]}

DESCRIPTION:
{self.description_text[:3000]}"""
        
        response = self._ollama_call(prompt, system_prompt)
        return self._extract_json_from_response(response, {"score": 0.5, "findings": ["Analysis incomplete"]})
    
    # ========================================================================
    # CALCULATION AND UTILITY METHODS
    # ========================================================================
    
    def _calculate_confidence(
        self,
        fingerprint: Dict,
        anchor: Dict,
        hallucination: Dict,
        drawing: Dict
    ) -> float:
        """
        Calculate weighted confidence score.
        
        Weights based on skill.md methodology:
        - Stylometric Fingerprinting: 30%
        - Anchor Similarity: 40%
        - Technical Hallucination: 20%
        - Drawing Consistency: 10%
        """
        fp_score = fingerprint.get("score", 0.5) * 0.30
        anchor_score = anchor.get("similarity", 0.5) * 0.40
        hall_score = hallucination.get("score", 0.5) * 0.20
        draw_score = drawing.get("score", 0.5) * 0.10
        
        total = fp_score + anchor_score + hall_score + draw_score
        
        return max(0.0, min(1.0, total))
    
    def _extract_json_from_response(self, response: str, fallback: Dict) -> Dict:
        """Extract JSON from Ollama response."""
        try:
            if "{" in response and "}" in response:
                json_start = response.index("{")
                json_end = response.rindex("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            print(f"     ⚠️ JSON extraction failed: {e}")
        
        return fallback
    
    def _get_risk_level(self, confidence: float) -> str:
        """Determine risk level from confidence score."""
        if confidence >= 0.75:
            return "HIGH"
        elif confidence >= 0.60:
            return "MEDIUM"
        elif confidence >= 0.40:
            return "LOW"
        else:
            return "MINIMAL"
    
    def _generate_recommendations(
        self, 
        confidence: float, 
        fingerprint: Dict, 
        anchor: Dict,
        drawing: Dict
    ) -> List[str]:
        """Generate actionable recommendations."""
        recs = []
        
        # Priority: Anchor similarity (strongest signal)
        anchor_sim = anchor.get("similarity", 0.5)
        if anchor_sim > 0.75:
            recs.append("🚨 CRITICAL: High anchor similarity (>75%) - strong AI signal")
            recs.append("   AI generated very similar text when given same claims")
            recs.append("   Action: Manual review required before filing")
        
        # Confidence-based recommendations
        if confidence >= 0.75:
            recs.append("⚠️ HIGH RISK: Strong AI indicators detected")
            recs.append("   Action: Perform thorough manual review")
            recs.append("   Action: Request author revision to reduce formulaic language")
        elif confidence >= 0.60:
            recs.append("⚠️ MEDIUM RISK: Moderate AI indicators detected")
            recs.append("   Action: Spot-check sections with repetitive patterns")
            recs.append("   Action: Verify technical accuracy of descriptions")
        elif confidence >= 0.40:
            recs.append("✓ LOW RISK: Minimal AI indicators")
            recs.append("   Consider: Minor edits to improve natural variation")
        else:
            recs.append("✓ MINIMAL RISK: No significant AI signals detected")
            recs.append("   Content appears to be human-written")
        
        # Add specific findings
        for finding in fingerprint.get("findings", [])[:2]:
            recs.append(f"• Fingerprint: {finding}")
        
        for finding in anchor.get("findings", [])[:2]:
            recs.append(f"• Anchor: {finding}")
        
        return recs
    
    def _print_summary(self, result: Dict[str, Any]):
        """Print analysis summary."""
        print(f"\n{'='*60}")
        print("📊 AI DETECTION RESULT")
        print(f"{'='*60}")
        print(f"Analysis Mode: LOCAL (Ollama)")
        print(f"Model: {result.get('ollama_model', 'unknown')}")
        print(f"AI Generated: {'YES ⚠️' if result['is_ai_generated'] else 'NO ✓'}")
        print(f"Confidence: {result['confidence_score']:.1%}")
        print(f"Risk Level: {result['risk_level']}")
        print(f"{'='*60}")
        
        scores = result.get("detailed_scores", {})
        print("\n📈 Detailed Scores:")
        print(f"  Stylometric Fingerprint: {scores.get('fingerprint', 0):.1%} (weight: 30%)")
        print(f"  Anchor Similarity: {scores.get('anchor_similarity', 0):.1%} (weight: 40%) 👈 Strongest")
        print(f"  Technical Hallucination: {scores.get('hallucination', 0):.1%} (weight: 20%)")
        print(f"  Drawing Consistency: {scores.get('drawing', 0):.1%} (weight: 10%)")
        
        print("\n🔍 Key Findings:")
        
        # Fingerprint findings
        fp_findings = result.get("fingerprint_analysis", {}).get("findings", [])
        if fp_findings:
            print("  Stylometric:")
            for finding in fp_findings[:2]:
                print(f"    • {finding}")
        
        # Anchor findings
        anchor_findings = result.get("anchor_analysis", {}).get("findings", [])
        if anchor_findings:
            print("  Anchor Comparison:")
            for finding in anchor_findings[:2]:
                print(f"    • {finding}")
        
        print("\n📋 Recommendations:")
        for i, rec in enumerate(result.get("recommendations", []), 1):
            print(f"  {i}. {rec}")
        
        print(f"\n{'='*60}\n")
    
    def _save_result(self, result: Dict[str, Any]):
        """Save result to JSON file."""
        output_file = "ai_detection_result.json"
        output_path = os.path.join(self.input_dir, output_file)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"✓ Results saved to: {output_path}\n")
        except Exception as e:
            print(f"✗ Error saving results: {e}\n")


if __name__ == "__main__":
    # Setup paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    analyzer_dir = os.path.dirname(current_dir)
    document_dir = os.path.join(analyzer_dir, "document_text_output")
    
    print("="*60)
    print("AI PATENT DETECTION - LOCAL MODE (Ollama)")
    print("="*60)
    print("100% Privacy-Focused - No Cloud Services")
    print("="*60)
    print(f"\nLooking for documents in: {document_dir}")
    print("\n💡 Requirements:")
    print("   - Ollama must be running: ollama serve")
    print("   - Model must be available: ollama pull gpt-oss:120b-cloud")
    print("\n")
    
    try:
        analyzer = ai_detect_analyse(input_dir=document_dir)
        result = analyzer.run_analysis()
        
        print("\n" + "="*60)
        print("Analysis complete! Check ai_detection_result.json for full details.")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Start Ollama: ollama serve")
        print("  2. Pull model: ollama pull gpt-oss:120b-cloud")
        print("  3. Check model is running: ollama list")
        print("  4. Test Ollama: curl http://localhost:11434/api/tags")
