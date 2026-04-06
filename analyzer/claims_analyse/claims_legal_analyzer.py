"""
=========================
Patent Legal Analyzer for EPO + NIPO Standards
Analyzes Enablement (Art. 83 EPC / §8), Clarity (Art. 84 EPC), Support (Art. 84 EPC)
"""

import json
from typing import Optional, Dict, Any

from claims_config import AnalyzerConfig
from claims_config.legal_prompts import LegalAnalysisPrompts
from claims_core import OllamaClient
from claims_core.legal_models import (
    EnablementResult,
    ClarityResult,
    SupportResult,
    LegalAnalysisResult
)
from claims_utils import parse_json_safe, truncate_text
from claims_utils.guideline_loader import GuidelineLoader


class PatentLegalAnalyzer:
    """
    Patent Legal Analyzer for EPO + NIPO examination.
    
    Analyzes patent documents for:
    - Enablement (Art. 83 EPC / §8 Patentloven)
    - Clarity (Art. 84 EPC)
    - Support (Art. 84 EPC)
    
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
        print("⚖️ PATENT LEGAL ANALYSIS - EPO + NIPO")
        print(f"{'='*70}")
        print("Legal Framework: Art. 83 EPC, Art. 84 EPC, §8 Patentloven")
        print(f"{'='*70}\n")
        
        # Phase 1: Enablement Analysis
        print("Step 1/4: Enablement analysis (Art. 83 EPC / §8)...")
        enablement_result = self._analyze_enablement(claims, description, drawings)
        
        # Phase 2: Clarity Analysis
        print("Step 2/4: Clarity analysis (Art. 84 EPC)...")
        clarity_result = self._analyze_clarity(claims)
        
        # Phase 3: Support Analysis
        print("Step 3/4: Support analysis (Art. 84 EPC)...")
        support_result = self._analyze_support(claims, description, drawings)
        
        # Phase 4: Overall Assessment
        print("Step 4/4: Overall assessment...")
        overall = self._overall_assessment(
            enablement_result,
            clarity_result,
            support_result
        )
        
        # Build final result
        result = LegalAnalysisResult(
            enablement=enablement_result,
            clarity=clarity_result,
            support=support_result,
            risk_level=overall["risk_level"],
            summary=overall["summary"],
            critical_issues=overall["critical_issues"],
            recommendations=overall["recommendations"],
            examination_decision=overall["examination_decision"]
        )
        
        # Print summary
        print(result.get_summary_report())
        
        return result
    
    def _analyze_enablement(
        self,
        claims: str,
        description: str,
        drawings: Optional[str]
    ) -> EnablementResult:
        """
        Analyze enablement (Art. 83 EPC / §8 Patentloven).
        
        Checks if invention is disclosed clearly and completely enough
        for a skilled person to carry it out.
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.ENABLEMENT_USER,
            claims=truncate_text(claims, 6000),
            description=truncate_text(description, 8000),
            drawings=truncate_text(drawings, 2000) if drawings else "Not provided"
        )
        
        sys_prompt = LegalAnalysisPrompts.ENABLEMENT_SYSTEM
        if self.enablement_guidelines:
            sys_prompt += f"\n\nOFFICIAL GUIDELINES TO APPLY:\n{self.enablement_guidelines}"
            
        response = self.client.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        
        result_dict = parse_json_safe(response, {
            "status": "NOT_ENABLED",
            "issues": ["Analysis incomplete"],
            "missing_elements": [],
            "technical_deficiencies": [],
            "reproducibility_score": 0.5,
            "confidence": "LOW"
        })
        
        return EnablementResult(
            status=result_dict.get("status", "NOT_ENABLED"),
            issues=result_dict.get("issues", []),
            missing_elements=result_dict.get("missing_elements", []),
            technical_deficiencies=result_dict.get("technical_deficiencies", []),
            reproducibility_score=result_dict.get("reproducibility_score", 0.5),
            confidence=result_dict.get("confidence", "LOW")
        )
    
    def _analyze_clarity(self, claims: str) -> ClarityResult:
        """
        Analyze claim clarity (Art. 84 EPC).
        
        Checks if claims are clear, precise, and unambiguous.
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.CLARITY_USER,
            claims=truncate_text(claims, 6000)
        )
        
        sys_prompt = LegalAnalysisPrompts.CLARITY_SYSTEM
        if self.clarity_guidelines:
            sys_prompt += f"\n\nOFFICIAL GUIDELINES TO APPLY:\n{self.clarity_guidelines}"

        response = self.client.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        
        result_dict = parse_json_safe(response, {
            "status": "UNCLEAR",
            "issues": ["Analysis incomplete"],
            "vague_terms": [],
            "undefined_terms": [],
            "ambiguous_phrases": [],
            "clarity_score": 0.5,
            "confidence": "LOW"
        })
        
        return ClarityResult(
            status=result_dict.get("status", "UNCLEAR"),
            issues=result_dict.get("issues", []),
            vague_terms=result_dict.get("vague_terms", []),
            undefined_terms=result_dict.get("undefined_terms", []),
            ambiguous_phrases=result_dict.get("ambiguous_phrases", []),
            clarity_score=result_dict.get("clarity_score", 0.5),
            confidence=result_dict.get("confidence", "LOW")
        )
    
    def _analyze_support(
        self,
        claims: str,
        description: str,
        drawings: Optional[str]
    ) -> SupportResult:
        """
        Analyze claim support (Art. 84 EPC).
        
        Checks if claims are supported by the description.
        """
        prompt = LegalAnalysisPrompts.format_prompt(
            LegalAnalysisPrompts.SUPPORT_USER,
            claims=truncate_text(claims, 6000),
            description=truncate_text(description, 8000),
            drawings=truncate_text(drawings, 2000) if drawings else "Not provided"
        )
        
        sys_prompt = LegalAnalysisPrompts.SUPPORT_SYSTEM
        if self.support_guidelines:
            sys_prompt += f"\n\nOFFICIAL GUIDELINES TO APPLY:\n{self.support_guidelines}"

        response = self.client.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE
        )
        
        result_dict = parse_json_safe(response, {
            "status": "NOT_SUPPORTED",
            "issues": ["Analysis incomplete"],
            "unsupported_elements": [],
            "broader_than_description": [],
            "missing_embodiments": [],
            "support_score": 0.5,
            "confidence": "LOW"
        })
        
        return SupportResult(
            status=result_dict.get("status", "NOT_SUPPORTED"),
            issues=result_dict.get("issues", []),
            unsupported_elements=result_dict.get("unsupported_elements", []),
            broader_than_description=result_dict.get("broader_than_description", []),
            missing_embodiments=result_dict.get("missing_embodiments", []),
            support_score=result_dict.get("support_score", 0.5),
            confidence=result_dict.get("confidence", "LOW")
        )
    
    def _overall_assessment(
        self,
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


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import os
    import sys
    
    print("="*70)
    print("⚖️ PATENT LEGAL ANALYZER - EPO + NIPO")
    print("="*70)
    print("Analyzes: Enablement (Art. 83) + Clarity (Art. 84) + Support (Art. 84)")
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
