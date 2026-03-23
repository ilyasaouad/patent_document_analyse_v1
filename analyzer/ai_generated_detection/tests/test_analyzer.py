from unittest.mock import patch, MagicMock
from ai_patent_analyzer import AIPatentAnalyzer
from config.settings import AnalyzerConfig
from core.models import DetectionResult

def test_analyzer_initialization():
    config = AnalyzerConfig(OLLAMA_MODEL="test-model")
    with patch("core.ollama_client.OllamaClient.test_connection", return_value=True):
        analyzer = AIPatentAnalyzer(input_dir=None, config=config)
    
    assert analyzer.config.OLLAMA_MODEL == "test-model"
    # Test fallback defaults
    assert analyzer.documents == []
    assert analyzer.description_text == ""

@patch("core.ollama_client.OllamaClient.generate")
def test_analyze_text(mock_generate):
    """Test full analysis flow using direct text injection."""
    
    # Mock behavior for different phases based on the prompt content
    def side_effect(prompt, **kwargs):
        if "fingerprint" in prompt.lower():
            return '{"score": 0.8, "findings": ["AI detected"]}'
        elif "anchor" in prompt.lower() or "summary" in prompt.lower():
            # Generate anchor phase or Compare anchor phase
            return '{"similarity": 85, "findings": ["Very similar"]}'
        elif "unsupported" in prompt.lower():
            return '{"score": 0.2, "findings": []}'
        elif "enablement" in prompt.lower():
            return '{"enablement_conclusion": "ENABLED", "missing_elements": [], "technical_deficiencies": []}'
        elif "alignment" in prompt.lower():
            return '{"score": 0.4, "findings": ["Minor"]}'
        
        # Default response
        return '{"score": 0.5, "findings": []}'
        
    mock_generate.side_effect = side_effect
    
    config = AnalyzerConfig()
    with patch("core.ollama_client.OllamaClient.test_connection", return_value=True):
        analyzer = AIPatentAnalyzer(input_dir=None, config=config)
        
    result = analyzer.analyze_text(
        text="A formal patent description",
        claims="Patent claims",
        drawings="Patent drawings"
    )
    
    # Should be valid result
    assert isinstance(result, DetectionResult)
    assert result.confidence_score > 0.0
    assert result.risk_level in ["MINIMAL", "LOW", "MEDIUM", "HIGH"]
    assert "fingerprint" in result.feature_scores
