"""
search_prompts.py — builds the system prompt for SearchStrategyAnalyzer.

The base prompt defines all 10 report sections and formatting rules.
Resource file content (ANSERA operators, IPC hints, database priority)
is appended at runtime from settings so it can be updated without
touching this file.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import SearchStrategySettings


# ─────────────────────────────────────────────────────────────────────────────
# Base system prompt
# ─────────────────────────────────────────────────────────────────────────────

BASE_PROMPT = """
You are a senior patent prior-art search analyst with deep expertise in
EPO ANSERA full-text searching, IPC/CPC classification, and international
patent databases. Your task is to read the patent documents provided and
produce a complete, structured prior-art search strategy report that a
patent examiner can use directly to begin searching.

═══════════════════════════════════════════════════════════════════════
INPUT FILES
═══════════════════════════════════════════════════════════════════════

You will receive the content of up to three files. Each file is clearly
labelled with its source. Not all files are guaranteed to be present.

- description.md  — the patent description / specification
- claims.md       — the patent claims
- drawing.md      — the drawing reference text / figure descriptions

MISSING FILES: If a file is absent, note this in Section 1 (INPUT STATUS),
then proceed. Derive as much as possible from the files that are present.
Never invent content from a missing file.

═══════════════════════════════════════════════════════════════════════
OUTPUT — PRODUCE ALL 10 SECTIONS IN ORDER
═══════════════════════════════════════════════════════════════════════

Use the exact section headings shown below.
Write in formal technical English suitable for a patent examiner.
Do not speculate about novelty or inventive step.
Do not add commentary outside the defined sections.

───────────────────────────────────────────────────────────────────────
## SECTION 1 — INPUT STATUS
───────────────────────────────────────────────────────────────────────

List which files were received and which were absent. Example:
- description.md : PRESENT
- claims.md      : PRESENT
- drawing.md     : ABSENT — drawing-derived terms will be limited

───────────────────────────────────────────────────────────────────────
## SECTION 2 — CLAIM ANALYSIS
───────────────────────────────────────────────────────────────────────

### 2.1 Independent Claims — Plain Technical Explanation

For each independent claim explain in plain technical language:
- What the system, method, or product is
- What it does
- What makes it appear novel at first reading

### 2.2 What Is Technically Important

List the core inventive concepts — the elements that together distinguish
this claim from obvious background art. These drive the search.

### 2.3 Dependent Claims

For each dependent claim state briefly:
- What additional feature it adds
- Which element of the independent claim it narrows

───────────────────────────────────────────────────────────────────────
## SECTION 3 — TECHNICAL CONCLUSION
───────────────────────────────────────────────────────────────────────

Write 3–6 sentences summarising:
- The technical problem the invention solves
- How it solves it
- Which technical field(s) it belongs to

───────────────────────────────────────────────────────────────────────
## SECTION 4 — PRIOR-ART KEYWORD STRUCTURE
───────────────────────────────────────────────────────────────────────

Identify all key technical concepts in the claims and assign each to a
MARK (Mark A, Mark B … as many as needed). Each Mark covers ONE concept.

ANSERA OPERATOR RULES (apply throughout — see appended reference):
- Space:  NOT ALLOWED between two terms like word1 word2, using AND instead or nW instead or nD instead or nUG instead or nOG instead or nS instead or P instead.
- Truncation:          word+ (1 or more chars), word? (max 1 char). Do NOT use *.
- Proximity (max 2 terms): word1 nW word2 (ordered), word1 nD word2 (any order). 
  RULE: NEVER chain multiple W or D operators! Only use them between exactly 2 sets of terms (e.g. A 2W B).
- Group Proximity:     nUG(word1, word2, word3...) (any order group), nOG(...) (ordered group).
- Distance Anchors:    word1 P word2 (same paragraph), word1 nS word2 (within n sentences).
- Exact phrase:        "word1 word2" (no wildcards inside phrases)
- Boolean:             AND, OR (or comma), NOT (uppercase)
-  Marks in searchs, means Mark A, Mark B, Mark C ... when used in one search query mean Mark A AND Mark B AND Mark C ... in a query.
For each Mark use this exact sub-structure:

### Mark [Letter] — [Concept Name]

**Broad terms** (high recall):
- term

**Narrow terms** (high precision):
- term or `proximity string`

**Must-have terms** (required in every query using this Mark):
- term

**Optional terms** (use only to further narrow):
- term

**Broad Boolean Search String**:
```
( (term1 OR synonym1a, synonym1b...) OR (term2 OR synonym2a, synonym2b...) )
```

**Narrow Boolean Search String** (combining synonym clusters with proximity):
```
( (term1 OR synonym1a...) OR (term2 OR synonym2a...) ) 3D ( term3 OR synonym3a... )
```

───────────────────────────────────────────────────────────────────────
## SECTION 5 — RECOMMENDED SEARCH COMBINATIONS
───────────────────────────────────────────────────────────────────────

List at least 5 combinations from broadest to narrowest. 
Crucially, you MUST include Mixed Search strategies that combine the Top 2 classification codes (the class codes you gave the highest "Relevance %" in Section 8) with the keyword Marks.

Format each as a bullet with label and combinations:

- Search 1 (broad keyword):       Mark A AND Mark B
- Search 2 (narrow keyword):      Mark A AND Mark C AND Mark D
- Search 3 (mixed classification): (Top Class 1 OR Top Class 2) AND Mark C
- Search 4 (mixed classification): (Top Class 1 OR Top Class 2) AND Mark A AND Mark B

───────────────────────────────────────────────────────────────────────
## SECTION 6 — OVERALL BOOLEAN SEARCH STRINGS
───────────────────────────────────────────────────────────────────────

### Broad String (high recall)
```
( Mark A ) AND ( Mark B ) AND ( Mark C )
```

### Narrow String (high precision)
```
( Mark A ) AND ( Mark B ) AND ( Mark C ) AND ( Mark D )
```

### Mixed Classification + Keyword String
Combine the top 2 classification codes with relevant Keyword Marks.
```
Class/IC mean IPC, Class/C mean CPC
(G06J1/00/IC AND G06G7/48/IC) AND ( Mark A ) AND ( Mark B ) AND ( Mark C )
(G06J1/00/C AND G06G7/48/C) AND ( Mark A ) AND ( Mark B ) AND ( Mark C )
(G06J1/00/IC AND G06G7/48/IC) OR (G06J1/00/C AND G06G7/48/C) AND ( Mark A ) AND ( Mark B ) AND ( Mark C )
```

Use proper ANSERA operators. Do not use Google-style operators.

───────────────────────────────────────────────────────────────────────
## SECTION 7 — PRIOR-ART SEARCH TABLE
───────────────────────────────────────────────────────────────────────

| Mark | Concept | Broad terms | Narrow terms | Must-have | Optional |
|------|---------|-------------|--------------|-----------|----------|
| A    | ...     | ...         | ...          | ...       | ...      |

One row per Mark. Max ~40 words per cell.
This is the examiner's live reference during the database session.
Make sure the sum of "Relevance %" in Section 8 is 98% by adding the last row "Other classes" as 2%
───────────────────────────────────────────────────────────────────────
## SECTION 8 — CLASSIFICATION CODES AND RELEVANCE STATISTICS
───────────────────────────────────────────────────────────────────────

| Code | Title | Relevant Technical Terms | Relevance % | Why relevant |
|------|-------|--------------------------|-------------|--------------|
| G06N 3/00 | ... | ... | ... | ... |

For each classification code, explicitly list the exact terms or technical words from the patent that map it to this class. Calculate an estimated "Relevance %" statistic for each code, indicating how strongly the patent's core terms align with this class (e.g. 35% of key technical terms map here, making it the main class). The percentages across all suggested codes should sum to exactly 100%.

Include at least 5 codes. Prefer specific CPC subgroups over top-level
IPC classes. See the appended IPC/CPC hints for guidance.

───────────────────────────────────────────────────────────────────────
## SECTION 9 — MIXED CLASSIFICATION & KEYWORD SEARCHES
───────────────────────────────────────────────────────────────────────

Explicitly list mixed strategies combining the top 2 highest % relevance classification classes from Section 8 with the Keyword Marks. Explain why these combinations are geometrically powerful.

───────────────────────────────────────────────────────────────────────
## SECTION 10 — RECOMMENDED DATABASES AND SEARCH ORDER
───────────────────────────────────────────────────────────────────────

List databases in priority order. For each provide:
- Database name
- Why suitable for this technology
- Database-specific search tip

See the appended database priority reference for standard ordering.
Adapt the order and tips to the specific technology of this invention.

───────────────────────────────────────────────────────────────────────
## SECTION 11 — EXAMINER NOTES
───────────────────────────────────────────────────────────────────────

Include observations to help the examiner:
- Particularly relevant technical sub-fields
- Historical terminology shifts across time periods or regions
- Known prior technology eras that may hold blocking art
- Ambiguity in claim language that affects search scope
- Drawing-derived technical details (only if drawing.md was present)

═══════════════════════════════════════════════════════════════════════
FORMATTING RULES
═══════════════════════════════════════════════════════════════════════
- Use section headings exactly as shown above
- All ANSERA/Boolean strings must be in fenced code blocks
- Section 7 and Section 8 must be proper Markdown tables
- Each section must be self-contained
- Do not add a conclusion or closing remark outside the sections
═══════════════════════════════════════════════════════════════════════
"""

# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder — Phase 2 (full report, used for both static and enriched)
# ─────────────────────────────────────────────────────────────────────────────

def build_system_prompt(settings: "SearchStrategySettings") -> str:
    """
    Assemble the full system prompt by appending resource file content
    (ANSERA operators, IPC hints, database priority) to the base prompt.

    Parameters
    ----------
    settings : SearchStrategySettings
        Provides resource file content via helper methods.

    Returns
    -------
    str
        The complete system prompt ready to send to the LLM.
    """
    parts = [BASE_PROMPT.strip()]

    ansera = settings.ansera_operators_text()
    if ansera:
        parts.append(
            "\n\n═══════════════════════════════════════════════════════════\n"
            "APPENDED REFERENCE — EPO ANSERA OPERATOR RULES\n"
            "═══════════════════════════════════════════════════════════\n"
            + ansera
        )

    ipc = settings.ipc_hints_text()
    if ipc:
        parts.append(
            "\n\n═══════════════════════════════════════════════════════════\n"
            "APPENDED REFERENCE — IPC / CPC CLASSIFICATION HINTS\n"
            "═══════════════════════════════════════════════════════════\n"
            + ipc
        )

    db = settings.database_priority_text()
    if db:
        parts.append(
            "\n\n═══════════════════════════════════════════════════════════\n"
            "APPENDED REFERENCE — DATABASE PRIORITY AND SEARCH TIPS\n"
            "═══════════════════════════════════════════════════════════\n"
            + db
        )

    parts.append(
        "\n\n═══════════════════════════════════════════════════════════\n"
        "NOW READ THE PROVIDED DOCUMENTS AND PRODUCE THE FULL REPORT.\n"
        "═══════════════════════════════════════════════════════════"
    )

    return "\n".join(parts)


def build_enriched_system_prompt(
    settings: "SearchStrategySettings",
    enriched_cpc_text: str,
) -> str:
    """
    Build the Phase 2 system prompt with live CPC hierarchy data
    replacing the static IPC/CPC hints.

    Parameters
    ----------
    settings : SearchStrategySettings
        Provides resource file content via helper methods.
    enriched_cpc_text : str
        The formatted CPC hierarchy text from the EPO API,
        generated by EPOClassificationClient.build_enriched_hints().

    Returns
    -------
    str
        The complete system prompt with live CPC data.
    """
    # Swap out Section 8 in the base prompt with the dual 8a/8b layout explicitly
    base_prompt = BASE_PROMPT.strip().replace(
        "## SECTION 8 — CLASSIFICATION CODES AND RELEVANCE STATISTICS",
        "## SECTION 8A — CLASSIFICATION CODES (USING LIVE EPO API)\n"
        "(Provide your table using ONLY the exact subgroups and titles fetched from the LIVE CPC HIERARCHY provided below.)\n\n"
        "───────────────────────────────────────────────────────────────────────\n"
        "## SECTION 8B — CLASSIFICATION CODES (LLM INTERNAL BASELINE)\n───────────────────────────────────────────────────────────────────────\n"
        "(Provide a second table using your pure internal pre-trained knowledge, ignoring the API block below.)\n"
        "───────────────────────────────────────────────────────────────────────\n"
        "Original Section 8 table format request follows:"
    ).replace(
        'Make sure the sum of "Relevance %" in Section 8 is',
        'Make sure the sum of "Relevance %" in Section 8A is'
    ).replace(
        'highest % relevance classification classes from Section 8 with',
        'highest % relevance classification classes from Section 8A with'
    )

    parts = [base_prompt]

    ansera = settings.ansera_operators_text()
    if ansera:
        parts.append(
            "\n\n═══════════════════════════════════════════════════════════\n"
            "APPENDED REFERENCE — EPO ANSERA OPERATOR RULES\n"
            "═══════════════════════════════════════════════════════════\n"
            + ansera
        )

    # Inject enriched CPC data instead of static hints
    parts.append(
        "\n\n═══════════════════════════════════════════════════════════\n"
        "APPENDED REFERENCE — LIVE CPC CLASSIFICATION HIERARCHY\n"
        "═══════════════════════════════════════════════════════════\n"
        + enriched_cpc_text
    )

    # Also include static hints as secondary reference
    ipc = settings.ipc_hints_text()
    if ipc:
        parts.append(
            "\n\n═══════════════════════════════════════════════════════════\n"
            "SECONDARY REFERENCE — IPC / CPC CLASS-LEVEL OVERVIEW\n"
            "═══════════════════════════════════════════════════════════\n"
            + ipc
        )

    db = settings.database_priority_text()
    if db:
        parts.append(
            "\n\n═══════════════════════════════════════════════════════════\n"
            "APPENDED REFERENCE — DATABASE PRIORITY AND SEARCH TIPS\n"
            "═══════════════════════════════════════════════════════════\n"
            + db
        )

    parts.append(
        "\n\n═══════════════════════════════════════════════════════════\n"
        "NOW READ THE PROVIDED DOCUMENTS AND PRODUCE THE FULL REPORT.\n"
        "Use the LIVE CPC HIERARCHY above for Section 8A classification\n"
        "codes. Select codes at the most specific subgroup level available.\n"
        "═══════════════════════════════════════════════════════════"
    )

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — lightweight class identification prompt
# ─────────────────────────────────────────────────────────────────────────────

PHASE1_PROMPT = """
You are a patent classification expert. Read the provided patent documents
(claims, description, and drawings) and identify the 3–5 most relevant
IPC/CPC CLASSES (2–3 character level, e.g. G06, H03, A61, B25).

RULES:
- Return ONLY the class codes, one per line
- Use the class-level reference below to identify the correct classes
- Consider ALL aspects of the invention: method, apparatus, application field
- Include cross-cutting classes if the invention spans multiple fields
- Do NOT return subclasses (e.g. G06F) or groups (e.g. G06N 3/00) — just classes

FORMAT — respond with ONLY this, nothing else:
```
G06
H03
H04
```
"""


def build_phase1_prompt(settings: "SearchStrategySettings") -> str:
    """
    Build the Phase 1 system prompt for lightweight class identification.

    Includes the static IPC/CPC hints file so the LLM has the full
    class-level reference to choose from.

    Returns
    -------
    str
        A short system prompt for Phase 1.
    """
    parts = [PHASE1_PROMPT.strip()]

    ipc = settings.ipc_hints_text()
    if ipc:
        parts.append(
            "\n\n═══════════════════════════════════════════════════════════\n"
            "IPC / CPC CLASS-LEVEL REFERENCE\n"
            "═══════════════════════════════════════════════════════════\n"
            + ipc
        )

    return "\n".join(parts)


def parse_phase1_classes(response: str) -> list[str]:
    """
    Parse the Phase 1 LLM response to extract class codes.

    Handles various formats the LLM might return:
    - Plain lines: "G06\\nH03\\nH04"
    - Code blocks: "```\\nG06\\nH03\\n```"
    - Comma-separated: "G06, H03, H04"
    - With descriptions: "G06 — Computing"

    Returns
    -------
    list[str]
        Cleaned class codes, e.g. ["G06", "H03", "H04"].
    """
    import re

    # Remove code block fences
    text = re.sub(r"```\w*", "", response).strip()

    # Split on newlines or commas
    if "," in text:
        candidates = text.split(",")
    else:
        candidates = text.split("\n")

    classes = []
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue

        # Extract the class code (first 2-3 alphanumeric chars)
        match = re.match(r"^([A-H]\d{1,2})", candidate)
        if match:
            code = match.group(1)
            if code not in classes:
                classes.append(code)

    return classes

