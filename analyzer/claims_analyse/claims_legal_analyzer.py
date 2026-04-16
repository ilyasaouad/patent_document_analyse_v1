"""
=========================
Patent Legal Analyzer for NIPO Standards
Analyzes Enablement, Clarity, and Support (§ 8)
"""

import json
import re
from typing import Optional, Dict, Any

def clean_llm_output(text: str) -> str:
    """Removes leaked framework sections and neutralizes citations."""
    if not isinstance(text, str):
        return text
    # remove guideline section references like §1.1 or §4.10
    text = re.sub(r"§\d+\.\d+", "", text)
    # normalize broken citations
    text = re.sub(r"§\s*\d+\s*\d+-\d+", "Patent Act § 8 (2)", text)
    return text

from claims_config import AnalyzerConfig
from claims_config.legal_prompts import LegalAnalysisPrompts
from claims_core import OllamaClient
from claims_core.legal_models import (
    ClaimAnalysisResult,
    EnablementResult,
    ClarityResult,
    SupportResult,
    LegalAnalysisResult
)
from claims_utils import parse_json_safe, truncate_text
from claims_utils.guideline_loader import GuidelineLoader


class PatentLegalAnalyzer:
    """
    Patent Legal Analyzer for NIPO examination.
    
    Analyzes patent documents for:
    - Enablement (§8 Patentloven)
    - Clarity (§8 Patentloven)
    - Support (§8 Patentloven)
    
    Provides examination decision: GRANT, OBJECT, or FURTHER_EXAMINATION
    """
    
    def __init__(
        self,
        config: Optional[AnalyzerConfig] = None,
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize legal analyzer.
        
        Args:
            config: Configuration object (uses defaults if None)
            ollama_client: Existing Ollama client (creates new if None)
        """
        self.config = config or AnalyzerConfig()
        
        # Load guidelines
        loader = GuidelineLoader()
        self.enablement_guidelines = loader.get_enablement_guidelines()
        self.clarity_guidelines = loader.get_clarity_guidelines()
        self.support_guidelines = loader.get_support_guidelines()
        self.claim_analysis_guidelines = loader.get_claim_analysis_guidelines()
        
        self.combined_guidelines = f"""[INPUT LAYER]

=== ENABLEMENT FRAMEWORK ===
{self.enablement_guidelines or 'Not provided'}

=== CLARITY FRAMEWORK ===
{self.clarity_guidelines or 'Not provided'}

=== SUPPORT FRAMEWORK ===
{self.support_guidelines or 'Not provided'}

=== CLAIM ANALYSIS FRAMEWORK ===
{self.claim_analysis_guidelines or 'Not provided'}

=== LEGAL AUTHORITIES ===
- Norwegian Patents Act § 8 (2)
"""
        
        # Use provided client or create new one
        if ollama_client:
            self.client = ollama_client
        else:
            self.client = OllamaClient(
                model_name=self.config.OLLAMA_MODEL,
                base_url=self.config.OLLAMA_URL
            )
            
            # Test connection
            if not self.client.test_connection():
                raise ConnectionError("Cannot connect to Ollama for legal analysis")
    
    def analyze(
        self,
        claims: str,
        description: str,
        drawings: Optional[str] = None
    ) -> LegalAnalysisResult:
        """
        Run complete legal analysis on patent documents.
        
        Args:
            claims: Patent claims text
            description: Patent description text
            drawings: Optional drawings/figures text
        
        Returns:
            LegalAnalysisResult: Complete legal analysis
        """
        print(f"\n{'='*70}")
        print("⚖️ PATENT LEGAL ANALYSIS - NIPO")
        print(f"{'='*70}")
        print("Legal Framework: Norwegian Patents Act § 8 (2)")
        print(f"{'='*70}\n")
        
        # Phase 1: Claim Analysis
        print("Step 1/5: Claim analysis (WHAT is the invention?)...")
        claim_analysis_result = self._analyze_claim_analysis(claims, description)

        # Phase 2: Enablement Analysis
        print("Step 2/5: Enablement analysis (CAN it be carried out?)...")
        enablement_result = self._analyze_enablement(claims, description, drawings)
        
        # Phase 3: Clarity Analysis
        print("Step 3/5: Clarity analysis (IS it clear?)...")
        clarity_result = self._analyze_clarity(claims)
        
        # Phase 4: Support Analysis
        print("Step 4/5: Support analysis (IS it disclosed?)...")
        support_result = self._analyze_support(claims, description, drawings)
        
        # Phase 5: Overall Assessment
        print("Step 5/5: Legal synthesis (§ 8 (2) conclusion)...")
        overall = self._overall_assessment(
            claim_analysis_result,
            enablement_result,
            clarity_result,
            support_result
        )

        # Output: Formal Report Synthesis
        print("Drafting formal NIPO examination report...")
        formal_report = self._generate_formal_report(
            claim_analysis_result,
            enablement_result,
            clarity_result,
            support_result
        )
        
        # Build final result
        result = LegalAnalysisResult(
            claim_analysis=claim_analysis_result,
            enablement=enablement_result,
            clarity=clarity_result,
            support=support_result,
            risk_level=overall["risk_level"],
            summary=overall["summary"],
            critical_issues=overall["critical_issues"],
            recommendations=overall["recommendations"],
            examination_decision=overall["examination_decision"],
            formal_report=formal_report
        )
        
        # Print summary
        print(result.get_summary_report())
        
        return result
    
    def _analyze_claim_analysis(self, claims: str, description: str) -> ClaimAnalysisResult:
        """
        Analyze claim essential features (WHAT is the invention?).
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.CLAIM_ANALYSIS_USER,
            guidelines=self.claim_analysis_guidelines,
            claims=truncate_text(claims, 6000),
            description=truncate_text(description, 8000)
        )
        
        sys_prompt = LegalAnalysisPrompts.CLAIM_ANALYSIS_SYSTEM
            
        response = self.client.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        response = clean_llm_output(response)
        
        result_dict = parse_json_safe(response, {
            "status": "DEFICIENT",
            "status_reason": "Analysis incomplete or missing.",
            "issues": ["Analysis incomplete"],
            "essential_features": [],
            "missing_features": [],
            "analysis_score": 0.5,
            "confidence": "LOW",
            "detailed_issues": [],
            "guideline_version": "Unknown"
        })
        
        return ClaimAnalysisResult(
            status=result_dict.get("status", "DEFICIENT"),
            status_reason=result_dict.get("status_reason", ""),
            issues=result_dict.get("issues", []),
            essential_features=result_dict.get("essential_features", []),
            missing_features=result_dict.get("missing_features", []),
            analysis_score=result_dict.get("analysis_score", 0.5),
            confidence=result_dict.get("confidence", "LOW"),
            detailed_issues=result_dict.get("detailed_issues", []),
            guideline_version=result_dict.get("guideline_version")
        )

    def _analyze_enablement(
        self,
        claims: str,
        description: str,
        drawings: Optional[str]
    ) -> EnablementResult:
        """
        Analyze enablement (Norwegian Patents Act § 8 (2)).
        
        Checks if invention is disclosed clearly and completely enough
        for a skilled person to carry it out.
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.ENABLEMENT_USER,
            guidelines=self.combined_guidelines,
            claims=truncate_text(claims, 6000),
            description=truncate_text(description, 8000),
            drawings=truncate_text(drawings, 2000) if drawings else "Not provided"
        )
        
        sys_prompt = LegalAnalysisPrompts.ENABLEMENT_SYSTEM
            
        response = self.client.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        response = clean_llm_output(response)
        
        result_dict = parse_json_safe(response, {
            "status": "NOT_ENABLED",
            "status_reason": "Analysis incomplete or missing.",
            "issues": ["Analysis incomplete"],
            "missing_elements": [],
            "technical_deficiencies": [],
            "reproducibility_score": 0.5,
            "confidence": "LOW",
            "detailed_issues": [],
            "guideline_version": "Unknown"
        })
        
        return EnablementResult(
            status=result_dict.get("status", "NOT_ENABLED"),
            status_reason=result_dict.get("status_reason", ""),
            issues=result_dict.get("issues", []),
            missing_elements=result_dict.get("missing_elements", []),
            technical_deficiencies=result_dict.get("technical_deficiencies", []),
            reproducibility_score=result_dict.get("reproducibility_score", 0.5),
            confidence=result_dict.get("confidence", "LOW"),
            detailed_issues=result_dict.get("detailed_issues", []),
            guideline_version=result_dict.get("guideline_version")
        )
    
    def _analyze_clarity(self, claims: str) -> ClarityResult:
        """
        Analyze claim clarity (Norwegian Patents Act § 8 (2)).
        
        Checks if claims are clear, precise, and unambiguous.
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.CLARITY_USER,
            guidelines=self.combined_guidelines,
            claims=truncate_text(claims, 6000)
        )
        
        sys_prompt = LegalAnalysisPrompts.CLARITY_SYSTEM

        response = self.client.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        response = clean_llm_output(response)
        
        result_dict = parse_json_safe(response, {
            "status": "UNCLEAR",
            "status_reason": "Analysis incomplete or missing.",
            "issues": ["Analysis incomplete"],
            "vague_terms": [],
            "undefined_terms": [],
            "ambiguous_phrases": [],
            "clarity_score": 0.5,
            "confidence": "LOW",
            "detailed_issues": [],
            "guideline_version": "Unknown"
        })
        
        return ClarityResult(
            status=result_dict.get("status", "UNCLEAR"),
            status_reason=result_dict.get("status_reason", ""),
            issues=result_dict.get("issues", []),
            vague_terms=result_dict.get("vague_terms", []),
            undefined_terms=result_dict.get("undefined_terms", []),
            ambiguous_phrases=result_dict.get("ambiguous_phrases", []),
            clarity_score=result_dict.get("clarity_score", 0.5),
            confidence=result_dict.get("confidence", "LOW"),
            detailed_issues=result_dict.get("detailed_issues", []),
            guideline_version=result_dict.get("guideline_version")
        )
    
    def _analyze_support(
        self,
        claims: str,
        description: str,
        drawings: Optional[str]
    ) -> SupportResult:
        """
        Analyze claim support (Norwegian Patents Act § 8 (2)).
        
        Checks if claims are supported by the description.
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.SUPPORT_USER,
            guidelines=self.combined_guidelines,
            claims=truncate_text(claims, 6000),
            description=truncate_text(description, 8000),
            drawings=truncate_text(drawings, 2000) if drawings else "Not provided"
        )
        
        sys_prompt = LegalAnalysisPrompts.SUPPORT_SYSTEM

        response = self.client.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        response = clean_llm_output(response)
        
        result_dict = parse_json_safe(response, {
            "status": "NOT_SUPPORTED",
            "status_reason": "Analysis incomplete or missing.",
            "issues": ["Analysis incomplete"],
            "unsupported_elements": [],
            "broader_than_description": [],
            "missing_embodiments": [],
            "support_score": 0.5,
            "confidence": "LOW",
            "detailed_issues": [],
            "guideline_version": "Unknown"
        })
        
        return SupportResult(
            status=result_dict.get("status", "NOT_SUPPORTED"),
            status_reason=result_dict.get("status_reason", ""),
            issues=result_dict.get("issues", []),
            unsupported_elements=result_dict.get("unsupported_elements", []),
            broader_than_description=result_dict.get("broader_than_description", []),
            missing_embodiments=result_dict.get("missing_embodiments", []),
            support_score=result_dict.get("support_score", 0.5),
            confidence=result_dict.get("confidence", "LOW"),
            detailed_issues=result_dict.get("detailed_issues", []),
            guideline_version=result_dict.get("guideline_version")
        )
    
    def _overall_assessment(
        self,
        claim_analysis: ClaimAnalysisResult,
        enablement: EnablementResult,
        clarity: ClarityResult,
        support: SupportResult
    ) -> Dict[str, Any]:
        """
        Generate overall examination assessment.
        
        Combines all three analyses to determine risk level and decision.
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.OVERALL_ASSESSMENT_USER,
            claim_analysis_result=json.dumps({
                "status": claim_analysis.status,
                "issues": claim_analysis.issues,
                "missing_features": claim_analysis.missing_features
            }, indent=2),
            enablement_result=json.dumps({
                "status": enablement.status,
                "issues": enablement.issues,
                "missing_elements": enablement.missing_elements
            }, indent=2),
            clarity_result=json.dumps({
                "status": clarity.status,
                "issues": clarity.issues,
                "vague_terms": clarity.vague_terms
            }, indent=2),
            support_result=json.dumps({
                "status": support.status,
                "issues": support.issues,
                "unsupported_elements": support.unsupported_elements
            }, indent=2)
        )
        
        response = self.client.generate(
            prompt=prompt,
            system_prompt=LegalAnalysisPrompts.OVERALL_ASSESSMENT_SYSTEM,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        
        return parse_json_safe(response, {
            "risk_level": "HIGH",
            "summary": "Overall assessment incomplete",
            "critical_issues": ["Assessment failed"],
            "recommendations": ["Manual review required"],
            "examination_decision": "FURTHER_EXAMINATION"
        })

    def _generate_formal_report(
        self,
        claim_analysis: ClaimAnalysisResult,
        enablement: EnablementResult,
        clarity: ClarityResult,
        support: SupportResult
    ) -> str:
        """
        Synthesizes the JSON findings into a formal Norwegian Patent Office examiner report.
        Disables strict JSON formatting to allow unstructured prose.
        """
        # Serialize the findings back to JSON so the LLM can read them natively
        ca_json = json.dumps(claim_analysis.__dict__, default=lambda x: str(x), indent=2)
        enb_json = json.dumps(enablement.__dict__, default=lambda x: str(x), indent=2)
        clr_json = json.dumps(clarity.__dict__, default=lambda x: str(x), indent=2)
        sup_json = json.dumps(support.__dict__, default=lambda x: str(x), indent=2)
        
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.FORMAL_REPORT_USER,
            claim_analysis_result=ca_json,
            enablement_result=enb_json,
            clarity_result=clr_json,
            support_result=sup_json
        )

        response = self.client.generate(
            prompt=prompt,
            system_prompt=LegalAnalysisPrompts.FORMAL_REPORT_SYSTEM,
            max_tokens=self.config.MAX_TOKENS,
            temperature=0.3,           # Slight temperature increase for better prose writing
            response_format=""         # DISABLE strict JSON constraint!
        )
        response = clean_llm_output(response)
        
        return response.strip()


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import os
    import sys
    
    print("="*70)
    print("⚖️ PATENT LEGAL ANALYZER - NIPO")
    print("="*70)
    print("Analyzes: Enablement, Clarity, and Support (§ 8)")
    print("="*70)
    
    # Example usage with test data
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    document_dir = os.path.join(parent_dir, "document_text_output")
    
    # Check if files exist, with fallbacks to auto-extracted files from Streamlit
    claims_file = os.path.join(document_dir, "claims.md")
    if not os.path.exists(claims_file):
        claims_file = os.path.join(document_dir, "claims_from_description.md")
        
    description_file = os.path.join(document_dir, "description.md")
    if not os.path.exists(description_file):
        description_file = os.path.join(document_dir, "description_only.md")
        
    drawings_file = os.path.join(document_dir, "drawings.md")
    
    if not os.path.exists(claims_file) or not os.path.exists(description_file):
        print("\n❌ Error: claims and description files required in document_text_output/")
        sys.exit(1)
    
    # Load documents
    print(f"\n📁 Loading documents from: {document_dir}\n")
    
    with open(claims_file, 'r') as f:
        claims = f.read()
    
    with open(description_file, 'r') as f:
        description = f.read()
    
    drawings = None
    if os.path.exists(drawings_file):
        with open(drawings_file, 'r') as f:
            drawings = f.read()
    
    try:
        # Initialize analyzer
        config = AnalyzerConfig()
        analyzer = PatentLegalAnalyzer(config=config)
        
        # Run analysis
        result = analyzer.analyze(
            claims=claims,
            description=description,
            drawings=drawings
        )
        
        # Save result
        output_path = os.path.join(document_dir, "legal_analysis_result.json")
        result.save_json(output_path)
        
        print("="*70)
        print("✅ Legal analysis complete!")
        print(f"   Decision: {result.examination_decision}")
        print(f"   Risk: {result.risk_level}")
        print(f"   Violations: {len(result.get_legal_violations())}")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("  1. Start Ollama: ollama serve")
        print("  2. Pull model: ollama pull gpt-oss:120b-cloud")
        sys.exit(1)
