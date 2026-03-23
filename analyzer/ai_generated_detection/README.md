

# AI Patent Detection Analyzer - Modular Architecture

Clean, maintainable codebase with separated concerns for production deployment.

## 📁 Project Structure

```
ai_patent_analyzer/
├── config/
│   ├── __init__.py           # Package init
│   ├── settings.py           # Configuration & thresholds
│   └── prompts.py            # All LLM prompt templates
│
├── core/
│   ├── __init__.py           # Package init
│   ├── ollama_client.py      # Ollama LLM client
│   └── models.py             # Data models (DetectionResult, PatentDocument)
│
├── utils/
│   ├── __init__.py           # Package init
│   └── helpers.py            # Utility functions (text processing, JSON parsing)
│
├── ai_patent_analyzer.py     # Main analyzer class
├── analyzer_config.json      # Optional runtime config (auto-generated)
└── README.md                 # This file
```

## 🎯 Module Responsibilities

### `config/` - Configuration & Prompts
**Files:** `settings.py`, `prompts.py`

**Purpose:** Centralize all configuration and prompt templates

**settings.py contains:**
- `AnalyzerConfig` - Main configuration dataclass
- LLM settings (model, URL, API key)
- Detection thresholds (AI detection, risk levels)
- Phase weights (fingerprint 30%, anchor 40%, hallucination 20%, drawing 10%)
- File matching patterns (description, claims, drawings)
- Configuration presets (Strict, Lenient, Fast)

**prompts.py contains:**
- All LLM system prompts
- All LLM user prompt templates
- Prompt formatting utilities

**Why separated:**
- Easy to tune detection without touching code
- Prompts can be A/B tested
- Configuration can be loaded from external files
- Presets allow different use cases

---

### `core/` - Core Functionality
**Files:** `ollama_client.py`, `models.py`

**Purpose:** Core business logic and data structures

**ollama_client.py contains:**
- `OllamaClient` - Local Ollama API client
- Connection testing
- Text generation with streaming support
- Model availability checking

**models.py contains:**
- `DetectionResult` - Typed output structure
- `PatentDocument` - Document representation
- JSON serialization helpers
- Result persistence

**Why separated:**
- Clean abstraction of LLM provider
- Easy to add new providers (GPT-OSS, Anthropic, etc.)
- Typed outputs ensure system compatibility
- Models define the contract with other systems

---

### `utils/` - Utility Functions
**Files:** `helpers.py`

**Purpose:** Reusable utility functions

**helpers.py contains:**
- `truncate_text()` - Smart text truncation at sentence boundaries
- `parse_json_safe()` - Robust JSON extraction from LLM responses
- `normalize_score()` - Score normalization to 0-1 range
- `extract_figure_references()` - Patent figure extraction
- `extract_element_references()` - Element number extraction
- `format_percentage()` - Percentage formatting
- `validate_json_structure()` - JSON validation

**Why separated:**
- DRY (Don't Repeat Yourself) principle
- Easier to test in isolation
- Reusable across different analyzers
- Clean separation from business logic

---

### `ai_patent_analyzer.py` - Main Analyzer
**Purpose:** Orchestration and analysis workflow

**Contains:**
- `AIPatentAnalyzer` - Main class
- Document loading and categorization
- Multi-phase analysis execution
- Result generation and display
- CLI entry point

**Why separated:**
- Single Responsibility: only orchestrates analysis
- Uses config, core, and utils modules
- Can be imported as a library
- Clean CLI interface

---

## 🚀 Usage

### Basic Usage (CLI)

```bash
# Using default settings
python ai_patent_analyzer.py

# Files are auto-detected from document_text_output/
# Looks for: description*.md, claim*.md, drawing.md
```

### As a Library

```python
from ai_patent_analyzer import AIPatentAnalyzer
from config import AnalyzerConfig

# Option 1: Use defaults
analyzer = AIPatentAnalyzer(input_dir="document_text_output")
result = analyzer.run_analysis()

# Option 2: Custom config
config = AnalyzerConfig(
    OLLAMA_MODEL="gpt-oss:120b-cloud",
    AI_DETECTION_THRESHOLD=0.7,
    WEIGHT_ANCHOR=0.50  # Increase anchor weight
)
analyzer = AIPatentAnalyzer(input_dir="document_text_output", config=config)
result = analyzer.run_analysis()

# Option 3: Analyze text directly
analyzer = AIPatentAnalyzer()
result = analyzer.analyze_text(
    text="Patent description...",
    claims="Claim 1. A system...",
    drawings="FIG. 1 shows..."
)

# Access results
print(f"AI Generated: {result.is_likely_ai_generated}")
print(f"Confidence: {result.confidence_score:.1%}")
print(f"Risk: {result.risk_level}")
print(f"Scores: {result.feature_scores}")
```

### Custom Configuration File

```json
{
  "OLLAMA_MODEL": "gpt-oss:120b-cloud",
  "AI_DETECTION_THRESHOLD": 0.65,
  "HIGH_RISK_THRESHOLD": 0.80,
  "WEIGHT_FINGERPRINT": 0.25,
  "WEIGHT_ANCHOR": 0.45,
  "WEIGHT_HALLUCINATION": 0.20,
  "WEIGHT_DRAWING": 0.10
}
```

Save as `analyzer_config.json` in the same directory.

---

## 🔧 Configuration Options

### LLM Settings
```python
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "gpt-oss:120b-cloud"
TEMPERATURE = 0.1  # Low = consistent, High = creative
MAX_TOKENS = 2048
```

### Detection Thresholds
```python
AI_DETECTION_THRESHOLD = 0.6   # Main threshold
HIGH_RISK_THRESHOLD = 0.75     # ≥75% = HIGH
MEDIUM_RISK_THRESHOLD = 0.60   # 60-75% = MEDIUM
LOW_RISK_THRESHOLD = 0.40      # 40-60% = LOW
```

### Phase Weights (must sum to 1.0)
```python
WEIGHT_FINGERPRINT = 0.30    # Stylometric analysis
WEIGHT_ANCHOR = 0.40         # Strongest signal!
WEIGHT_HALLUCINATION = 0.20  # Technical validation
WEIGHT_DRAWING = 0.10        # Drawing consistency
```

### File Matching Patterns
```python
DESCRIPTION_PATTERNS = ["description", "describtion"]
CLAIMS_PATTERNS = ["claim"]
DRAWING_PATTERNS = ["drawing"]
```

---

## 📊 Analysis Phases

### Phase 1: Stylometric Fingerprinting (30%)
**What:** Analyzes writing style patterns
**Detects:** Uniform sentences, repetitive transitions, lack of human quirks

### Phase 2: Anchor Method (40%) - STRONGEST
**What:** AI generates its own version, compares with original
**Detects:** High similarity (>75%) = strong AI signal

### Phase 3: Technical Hallucination (20%)
**What:** Finds unsupported technical terms
**Detects:** Terms in description not in claims

### Phase 4: Drawing Consistency (10%)
**What:** Compares description vs actual drawings
**Detects:** Missing figures, hallucinated element numbers

### Phase 5: Enablement Assessment (Bonus)
**What:** Checks if patent disclosure is sufficient
**Detects:** Missing implementation details

---

## 🎯 Output Format

### DetectionResult Object
```python
@dataclass
class DetectionResult:
    is_likely_ai_generated: bool        # True/False
    confidence_score: float             # 0.0-1.0
    risk_level: str                     # HIGH/MEDIUM/LOW/MINIMAL
    feature_scores: Dict[str, float]    # Individual phase scores
    detailed_analysis: Dict[str, Any]   # Full analysis results
    recommendations: List[str]          # Actionable recommendations
    applied_rules: List[str]            # Rules applied
    metadata: Dict[str, Any]            # Timestamp, config, etc.
```

### JSON Output
Saved to `document_text_output/ai_detection_result.json`:

```json
{
  "is_likely_ai_generated": true,
  "confidence_score": 0.732,
  "risk_level": "MEDIUM",
  "feature_scores": {
    "fingerprint": 0.68,
    "anchor_similarity": 0.85,
    "hallucination": 0.65,
    "drawing": 0.58
  },
  "detailed_analysis": {
    "fingerprint_analysis": {...},
    "anchor_analysis": {...},
    "hallucination_analysis": {...},
    "drawing_analysis": {...},
    "enablement_assessment": {...}
  },
  "recommendations": [
    "🚨 CRITICAL: High anchor similarity...",
    "⚠️ MEDIUM RISK: Moderate AI indicators..."
  ]
}
```

---

## 🛠️ Extending the System

### Add New Analysis Phase

1. **Add prompt to `config/prompts.py`:**
```python
class PromptTemplates:
    NEW_PHASE_SYSTEM = "..."
    NEW_PHASE_USER = "..."
```

2. **Add phase method to `ai_patent_analyzer.py`:**
```python
def _phase_new_check(self) -> Dict[str, Any]:
    prompt = PromptTemplates.format_prompt(...)
    response = self.client.generate(...)
    return parse_json_safe(response, fallback)
```

3. **Update weight calculation:**
```python
# In config/settings.py
WEIGHT_NEW_PHASE: float = 0.15

# Adjust other weights to sum to 1.0
WEIGHT_ANCHOR = 0.35  # Was 0.40
```

4. **Call in run_analysis():**
```python
new_phase = self._phase_new_check()
# Include in _calculate_confidence()
```

### Add New LLM Provider

1. **Create provider client in `core/`:**
```python
# core/anthropic_client.py
class AnthropicClient(LLMClient):
    def generate(...):
        # Implementation
```

2. **Update `AIPatentAnalyzer.__init__`:**
```python
if self.config.LLM_PROVIDER == "anthropic":
    self.client = AnthropicClient(...)
```

---

## 🧪 Testing

### Unit Tests (Recommended Structure)
```
tests/
├── test_config.py      # Test configuration loading
├── test_prompts.py     # Test prompt formatting
├── test_ollama.py      # Test Ollama client
├── test_helpers.py     # Test utility functions
└── test_analyzer.py    # Test main analyzer
```

### Example Test
```python
# tests/test_helpers.py
from utils import truncate_text, parse_json_safe

def test_truncate_text():
    text = "First sentence. Second sentence. Third sentence."
    result = truncate_text(text, 20)
    assert result == "First sentence."

def test_parse_json_safe():
    response = 'Some text {"score": 0.8, "findings": ["test"]} more text'
    result = parse_json_safe(response, {})
    assert result["score"] == 0.8
```

---

## 📋 Requirements

```
# requirements.txt
requests>=2.31.0
```

---

## 🔒 Privacy & Security

- **100% LOCAL** - All analysis runs on your machine
- **No cloud services** - Uses local Ollama only
- **No data transmission** - Patent data never leaves your system
- **Offline capable** - Works without internet

---

## 💡 Tips & Best Practices

### For Best Detection Accuracy:

1. **Use large model:** `gpt-oss:120b-cloud` > `llama3.2:3b`
2. **Provide all files:** description.md, claims.md, drawings.md
3. **Clean OCR:** Ensure drawings.md has clean OCR text
4. **Tune thresholds:** Adjust based on your use case

### Configuration Presets:

```python
# Strict (reduce false negatives)
from config import StrictConfig
config = StrictConfig()  # Lower thresholds

# Lenient (reduce false positives)
from config import LenientConfig
config = LenientConfig()  # Higher thresholds

# Fast (quicker analysis)
from config import FastConfig
config = FastConfig()  # Smaller text chunks
```

### Performance:

- **gpt-oss:120b-cloud:** 5-10 minutes per patent (high accuracy)
- **llama3.2:3b:** 1-2 minutes per patent (good accuracy)
- Increase `timeout` in `ollama_client.py` if needed

---

## 🐛 Troubleshooting

### "Cannot connect to Ollama"
```bash
ollama serve
ollama list
ollama pull gpt-oss:120b-cloud
```

### "Model not found"
```bash
ollama pull gpt-oss:120b-cloud
# Or update OLLAMA_MODEL in config
```

### "JSON extraction failed"
- Model may be struggling with JSON format
- Try larger model
- Check `parse_json_safe()` in `utils/helpers.py`

### "File not detected"
- Check filename matches patterns:
  - `description*.md` or `describtion*.md`
  - `claim*.md`
  - `drawing*.md`
- Update patterns in `config/settings.py` if needed

---

## 📝 License & Credits

Built for patent AI detection using local LLMs for maximum privacy.

**Methodology:** Multi-phase weighted analysis with patent-specific checks
**LLM:** Ollama (local, private)
**Model:** gpt-oss:120b-cloud (recommended) or llama3.2:3b (faster)

---

## 🚀 Quick Start Summary

```bash
# 1. Start Ollama
ollama serve

# 2. Pull model
ollama pull gpt-oss:120b-cloud

# 3. Place files in document_text_output/
#    - description.md (or description*.md)
#    - claims.md (or claim*.md)  
#    - drawings.md

# 4. Run analyzer
python ai_patent_analyzer.py

# 5. Check results
cat document_text_output/ai_detection_result.json
```

Done! 🎉
