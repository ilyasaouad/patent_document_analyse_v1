"""
core/models.py
==============
Data structures for document representation and detection results.
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any


@dataclass
class PatentDocument:
    """Represents a loaded patent document (description, claims, or drawings)."""
    file_name: str
    file_path: str
    content: str
    doc_type: str  # e.g., "description", "claims", "drawings", "unknown"


@dataclass
class DetectionResult:
    """Typed output structure for AI Detection results."""
    is_likely_ai_generated: bool
    confidence_score: float
    risk_level: str
    feature_scores: Dict[str, float]
    detailed_analysis: Dict[str, Any]
    recommendations: List[str]
    applied_rules: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save_json(self, output_path: str) -> None:
        """
        Serialize result to a JSON file.
        
        Args:
            output_path: Path to save the JSON file.
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
