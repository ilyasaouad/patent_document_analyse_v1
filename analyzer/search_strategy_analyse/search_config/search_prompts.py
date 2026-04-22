"""
search_prompts.py — modular system prompt components for SearchStrategyAnalyzer.

Divided into Task Blocks to allow for easier tuning of specific search 
strategy functions (Keywords, Classification, Boolean Logic, etc.)
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import json
import re

if TYPE_CHECKING:
    from .settings import SearchStrategySettings


# =============================================================================
# 1. TASK: PERSONA & INPUT (META)
# =============================================================================

TASK_META = """
You are a senior patent prior-art search analyst whose primary search tool is EPO ANSERA. Produce a structured ANSERA-ready search-strategy report from the provided files: claims, description, drawings.

MISSING FILES: If any file is absent, note it in SECTION 1 and proceed without inventing content.

Human-readable outputs required (concise):
Header: Field (1 line); Top 5 technical terms (bulleted).
"""

SECTION_1_INPUT = """
───────────────────────────────────────────────────────────────────────
## SECTION 1 — INPUT STATUS
───────────────────────────────────────────────────────────────────────
List which files were received and which were absent.
"""


# =============================================================================
# 2. TASK: TECHNICAL ANALYSIS
# =============================================================================

SECTION_2_CLAIMS = """
───────────────────────────────────────────────────────────────────────
## SECTION 2 — CLAIM ANALYSIS
───────────────────────────────────────────────────────────────────────
2.1 Independent claims: plain technical explanation (1–2 sentences).
2.2 Core inventive concepts: 4–8 bullets.
2.3 Dependent-claim narrowing elements: brief bullets.
"""

SECTION_3_CONCLUSION = """
───────────────────────────────────────────────────────────────────────
## SECTION 3 — TECHNICAL CONCLUSION
───────────────────────────────────────────────────────────────────────
3–6 sentences on the technical problem, solution, primary fields.
"""


# =============================================================================
# 3. TASK: KEYWORD & ANSERA STRUCTURE
# =============================================================================

SECTION_4_ANSERA = """
───────────────────────────────────────────────────────────────────────
## SECTION 4 — PRIOR-ART KEYWORD STRUCTURE (ANSERA)
───────────────────────────────────────────────────────────────────────
Identify concepts and assign them to Marks (Mark A, Mark B...).
For each Mark (A, B...), provide:
- Broad terms (high recall)
- Narrow terms (high precision / proximity)
- Must-have vs Optional
- ANSERA Boolean strings in fenced code blocks (use provided ANSERA operators exactly)
"""


# =============================================================================
# 4. TASK: SEARCH COMBINATIONS & BOOLEAN LOGIC
# =============================================================================

SECTION_5_6_STRATEGIES = """
───────────────────────────────────────────────────────────────────────
## SECTION 5 — RECOMMENDED SEARCH COMBINATIONS
───────────────────────────────────────────────────────────────────────
List at least 5 combinations (Broad -> Narrow combos). Include Mixed strategies combining classes+Marks.

───────────────────────────────────────────────────────────────────────
## SECTION 6 — BOOLEAN SEARCH STRINGS
───────────────────────────────────────────────────────────────────────
Provide Broad, Narrow, and Mixed (classification+keywords) ANSERA strings — each in fenced code blocks.
"""


# =============================================================================
# 5. TASK: CLASSIFICATION (DETERMINISTIC)
# =============================================================================

SECTION_7_TABLE = """
───────────────────────────────────────────────────────────────────────
## SECTION 7 — PRIOR-ART SEARCH TABLE
───────────────────────────────────────────────────────────────────────
Markdown table mapping Marks -> concepts -> search terms.
"""

# Dynamic Section 8 logic is handled by the builder functions below.
SECTION_8_GROUNDING_RULES = """### GROUNDING, NORMALIZATION, AND ANTI-HALLUCINATION RULES
- Do NOT invent CPC/IPC titles or live ANSERA outputs. If live data is absent, label Section 8A accordingly.
- Normalize technical phrases to canonical forms (e.g., "vector embedding", "information retrieval").
- Maximum 12 technical terms; each term must include importance 1-5.
- Elevate a term to High only if it appears in an independent claim or is concretely defined in the description.
- Relevance % across suggested classes (Section 8A or 8B) must sum to 100%.
"""


# =============================================================================
# 6. TASK: SEARCH OPS & NOTES
# =============================================================================

SECTION_9_10_11_RESOURCES = """
───────────────────────────────────────────────────────────────────────
## SECTION 9 — MIXED CLASSIFICATION & KEYWORD NOTES
───────────────────────────────────────────────────────────────────────
Short rationale explaining why the specific class + keyword intersections are powerful.

───────────────────────────────────────────────────────────────────────
## SECTION 10 — RECOMMENDED DATABASES & SEARCH ORDER
───────────────────────────────────────────────────────────────────────
Priority list with suitability reasons and database-specific search tips (ANSERA first).

───────────────────────────────────────────────────────────────────────
## SECTION 11 — EXAMINER NOTES & AMBIGUITY FLAGS
───────────────────────────────────────────────────────────────────────
List terms that could shift classification and why. Explain observations on terminology shifts or historical eras.
"""

FORMATTING_RULES = """
=======================
FORMATTING & VALIDATION RULES
=======================
- All ANSERA/Boolean strings must be in fenced code blocks.
- All tables must be Markdown tables.
- Use section headings exactly as shown.

ANSERA validation step (short):
Provide one example ANSERA query derived from top Mark.
Provide a 3-item checklist confirming operator correctness (proximity, truncation, grouping).

*** Machine-readable JSON (MANDATORY) ***
You MUST append the following JSON structure exactly at the end of your report inside a fenced json block (```json ... ```):
{
  "field": "...",
  "top_terms": ["t1", "t2", "t3", "t4", "t5"],
  "core_features": ["..."],
  "high_terms": [{"term": "...", "importance": 5}],
  "medium_terms": ["..."],
  "low_terms": ["..."],
  "primary_cpcs": [{"code":"G06F17/30", "reason":"...", "relevance_pct":60}],
  "alt_cpcs": [{"code":"G06N3/08", "reason":"...", "relevance_pct":40}],
  "ambiguity_flags": [{"term":"oscillatory representation", "issue":"may imply signal processing -> consider G06F3/01 if hardware/signals claimed"}]
}
"""


# =============================================================================
# BUILDER FUNCTIONS
# =============================================================================

def build_system_prompt(settings: "SearchStrategySettings") -> str:
    """Assembles the standard system prompt."""
    parts = [
        TASK_META,
        SECTION_1_INPUT,
        SECTION_2_CLAIMS,
        SECTION_3_CONCLUSION,
        SECTION_4_ANSERA,
        SECTION_5_6_STRATEGIES,
        SECTION_7_TABLE,
        "## SECTION 8 — CLASSIFICATION CODES AND RELEVANCE STATISTICS\n",
        SECTION_8_GROUNDING_RULES,
        SECTION_9_10_11_RESOURCES,
        FORMATTING_RULES
    ]
    
    # Append Resource references from settings
    parts.append("\n=== REFERENCE DATA ===")
    parts.append(f"ANSERA RULES:\n{settings.ansera_operators_text()}")
    parts.append(f"CLASSIFICATION HINTS:\n{settings.ipc_hints_text()}")
    parts.append(f"DATABASE PRIORITY:\n{settings.database_priority_text()}")
    
    return "\n".join(parts)


def build_enriched_system_prompt(
    settings: "SearchStrategySettings",
    enriched_cpc_text: str,
    phase1_data: dict | None = None,
) -> str:
    """Assembles the high-precision enriched prompt (Phase 2)."""
    
    # 1. Start with core report structure
    parts = [
        TASK_META,
        SECTION_1_INPUT,
        SECTION_2_CLAIMS,
        SECTION_3_CONCLUSION,
        SECTION_4_ANSERA,
        SECTION_5_6_STRATEGIES,
        SECTION_7_TABLE,
    ]
    
    # 2. Add the dynamic dual-classification block (8A/8B)
    parts.append(
        "## SECTION 8A — CLASSIFICATION CODES (USING LIVE EPO API)\n"
        "### MANDATORY TARGET RULE\n"
        "You MUST include the Main Classes (Subclasses, e.g., G06F) at the start of your table.\n"
        "Follow these with the specific CPC subgroups provided in the 'ALGORITHMICALLY RANKED CPC TARGETS' block.\n"
        "Use exact titles. Do not include confidence scores in the table code column.\n"
        "\n"
        "## SECTION 8B — CLASSIFICATION CODES (LLM INTERNAL BASELINE)\n"
        "(Provide a second independent table using your pre-trained knowledge.)\n"
    )
    
    parts.append(SECTION_8_GROUNDING_RULES)
    parts.append(SECTION_9_10_11_RESOURCES)
    parts.append(FORMATTING_RULES)
    
    # 3. Inject the analysis results (Ranked Targets + Terms)
    if phase1_data:
        analysis = [
            "\n=== PRELIMINARY TECHNICAL ANALYSIS (PHASE 1) ===",
            f"DOMAIN:  {phase1_data.get('domain', 'N/A')}",
            f"PROBLEM: {phase1_data.get('problem', 'N/A')}",
            f"METHOD:  {phase1_data.get('method', 'N/A')}\n",
        ]
        
        ranked = phase1_data.get('final_ranked_codes', [])
        
        # Identify Main Classes (Subclasses - first 4 chars)
        main_classes = sorted(list(set(n.symbol[:4] for n in ranked if len(n.symbol) >= 4)))
        if main_classes:
            analysis.append("MAIN CLASSES (SUBCLASSES) FOUND:")
            for mc in main_classes:
                analysis.append(f"- {mc}")
            analysis.append("")

        analysis.append("ALGORITHMICALLY RANKED CPC TARGETS (SPECIFIC SUBGROUPS):")
        for n in ranked:
            analysis.append(f"- {n.symbol} [Confidence: {n.score:.2f}] — {n.title}")
            
        analysis.append("\nRELEVANT TECHNICAL TERMS:")
        for t in phase1_data.get('terms', []):
            analysis.append(f"- {t.get('term')} (importance: {t.get('importance', '?')})")
            
        parts.append("\n".join(analysis))

    # 4. Append Live Reference Data
    parts.append("\n=== LIVE REFERENCE DATA (EPO API) ===")
    parts.append(enriched_cpc_text)
    
    parts.append("\n=== STATIC REFERENCE DATA ===")
    parts.append(f"ANSERA RULES:\n{settings.ansera_operators_text()}")
    parts.append(f"DATABASE PRIORITY:\n{settings.database_priority_text()}")
    
    return "\n".join(parts)


# =============================================================================
# Phase 1 - Extraction Prompt
# =============================================================================

PHASE1_PROMPT = """
You are a patent analysis expert. Extract the core technical essence to drive algorithmic classification.

=======================
STEP 1 - CORE INTENT
=======================
Summarize the technical Problem and Method in 1 sentence each.
Identify up to 3 high-level IPC/CPC classes (e.g. G06F, A61B, H04L).

=======================
STEP 2 - CPC SECTION
=======================
Select mandatory CPC sections (A, B, C, D, E, F, G, H, Y).

=======================
STEP 3 - TECHNICAL TERMS
=======================
Extract 10-15 specific technical phrases. Avoid generic stop-words.

=======================
STEP 4 - IMPORTANCE
=======================
Weight each term (1-5).

OUTPUT ONLY JSON:
{
  "problem": "...",
  "method": "...",
  "ipc_cpc_classes": ["G06", "..."],
  "cpc_sections": ["G", "..."],
  "domain": "...",
  "terms": [{"term": "...", "importance": 5}]
}
"""

def build_phase1_prompt(settings: "SearchStrategySettings") -> str:
    parts = [PHASE1_PROMPT.strip()]
    ipc = settings.ipc_hints_text()
    if ipc:
        parts.append("\n=== IPC / CPC REFERENCE ===\n" + ipc)
    return "\n".join(parts)

def parse_phase1_classes(response: str) -> list[str]:
    try:
        text = re.sub(r"```(?:json)?\s*|\s*```", "", response).strip()
        data = json.loads(text)
        if isinstance(data, dict) and "ipc_cpc_classes" in data:
            return [str(c).strip() for c in data["ipc_cpc_classes"] if c]
    except Exception:
        pass
    # Match symbols like G06 or G06F
    matches = re.findall(r"\b([A-HY]\d{1,2}[A-Z]?)\b", response)
    return list(dict.fromkeys(matches))
