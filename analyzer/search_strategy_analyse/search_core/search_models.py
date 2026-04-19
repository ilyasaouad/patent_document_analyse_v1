"""
search_models — data classes and parsing helpers for search strategy results.

Mirrors claims_core/legal_models.py in structure.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Sub-models for structured sections
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InputStatus:
    """Tracks which input files were available for analysis."""
    description_present: bool = False
    claims_present:      bool = False
    drawing_present:     bool = False

    def summary(self) -> str:
        parts = []
        parts.append("description.md : " + ("PRESENT" if self.description_present else "ABSENT"))
        parts.append("claims.md      : " + ("PRESENT" if self.claims_present      else "ABSENT"))
        parts.append("drawing.md     : " + ("PRESENT" if self.drawing_present     else "ABSENT"))
        return "\n".join(parts)

    def any_present(self) -> bool:
        return any([self.description_present, self.claims_present, self.drawing_present])


@dataclass
class KeywordMark:
    """Represents one Mark (A, B, C …) in the keyword structure."""
    label:         str = ""   # e.g. "A"
    concept:       str = ""   # e.g. "Hardware architecture"
    broad_terms:   List[str] = field(default_factory=list)
    narrow_terms:  List[str] = field(default_factory=list)
    must_have:     List[str] = field(default_factory=list)
    optional:      List[str] = field(default_factory=list)
    broad_query:   str = ""
    narrow_query:  str = ""


@dataclass
class SearchCombination:
    """One recommended search combination from Section 5."""
    label:       str = ""   # e.g. "Search 1 (broad)"
    marks_used:  List[str] = field(default_factory=list)   # e.g. ["A", "B"]
    description: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Main result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SearchStrategyResult:
    """
    Full structured result returned by SearchStrategyAnalyzer.analyze().

    The full_report field always holds the complete Markdown report.
    All other fields are convenience extracts parsed from that report.
    """

    # ── Raw output ────────────────────────────────────────────────────────────
    full_report: str = ""

    # ── Input tracking ────────────────────────────────────────────────────────
    input_status: InputStatus = field(default_factory=InputStatus)

    # ── Parsed convenience fields ─────────────────────────────────────────────
    technical_conclusion:    str = ""        # Section 3 text
    marks:                   List[KeywordMark] = field(default_factory=list)
    search_combinations:     List[SearchCombination] = field(default_factory=list)
    broad_boolean_string:    str = ""        # Section 6 broad string
    narrow_boolean_string:   str = ""        # Section 6 narrow string
    mixed_boolean_string:    str = ""        # Section 6 mixed classification string
    classification_codes:    List[str] = field(default_factory=list)  # Section 8
    classification_table:    str = ""        # Section 8 full table markdown
    mixed_search_analysis:   str = ""        # Section 9 mixed search strategies text
    examiner_notes:          str = ""        # Section 11 text

    # ── Status ────────────────────────────────────────────────────────────────
    status:        str = "SUCCESS"   # SUCCESS | PARTIAL | ERROR
    error_message: str = ""

    # ── Derived metrics ───────────────────────────────────────────────────────
    @property
    def num_marks(self) -> int:
        return len(self.marks)

    @property
    def num_search_combinations(self) -> int:
        return len(self.search_combinations)

    # ── Serialisation ─────────────────────────────────────────────────────────
    def get_summary_report(self) -> str:
        """Return the full Markdown report text."""
        return self.full_report

    def to_dict(self) -> dict:
        return {
            "status":                  self.status,
            "error_message":           self.error_message,
            "description_present":     self.input_status.description_present,
            "claims_present":          self.input_status.claims_present,
            "drawing_present":         self.input_status.drawing_present,
            "num_marks":               self.num_marks,
            "num_search_combinations": self.num_search_combinations,
            "classification_codes":    self.classification_codes,
            "technical_conclusion":    self.technical_conclusion[:300] + "..."
                                       if len(self.technical_conclusion) > 300
                                       else self.technical_conclusion,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_section(report: str, section_heading: str) -> str:
    """
    Extract the body text of a Markdown section identified by a heading keyword.
    Stops at the next heading of equal or higher level.
    Returns empty string if not found.
    """
    lines = report.splitlines()
    in_section = False
    collected: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_section:
                collected.append(line)
            continue

        is_heading = stripped.startswith("#")
        if is_heading and section_heading.lower() in stripped.lower():
            in_section = True
            continue

        if in_section:
            # Stop at any heading at ## level or higher
            if re.match(r"^#{1,2}\s", stripped):
                break
            collected.append(line)

    return "\n".join(collected).strip()


def count_marks(report: str) -> int:
    """Count how many Mark sections appear in the report."""
    return len(re.findall(r"(?im)^#+\s+Mark\s+[A-Z]\b", report))


def count_search_combinations(report: str) -> int:
    """Count numbered search combinations in Section 5."""
    return len(re.findall(r"(?im)^[-*]\s+Search\s+\d+", report))


def extract_marks(report: str) -> List[KeywordMark]:
    """
    Parse Mark sections from the report into KeywordMark objects.
    This is a best-effort parser — LLM output formatting may vary.
    """
    marks: List[KeywordMark] = []
    # Find all Mark headings
    pattern = re.compile(r"(?im)^#+\s+Mark\s+([A-Z])\s*[—–-]\s*(.+)$")
    matches = list(pattern.finditer(report))

    for i, match in enumerate(matches):
        label   = match.group(1).strip()
        concept = match.group(2).strip()

        # Extract text until next Mark or next ## section
        start = match.end()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(report)
        block = report[start:end]

        mark = KeywordMark(label=label, concept=concept)

        # Parse sub-sections by looking for bold headers
        def _extract_list(block: str, header: str) -> List[str]:
            pattern = re.compile(
                rf"(?im)\*\*{re.escape(header)}\*\*.*?\n(.*?)(?=\n\*\*|\Z)",
                re.DOTALL,
            )
            m = pattern.search(block)
            if not m:
                return []
            raw = m.group(1)
            items = re.findall(r"(?m)^[-*]\s+(.+)$", raw)
            return [item.strip() for item in items if item.strip()]

        mark.broad_terms  = _extract_list(block, "Broad terms")
        mark.narrow_terms = _extract_list(block, "Narrow terms")
        mark.must_have    = _extract_list(block, "Must-have terms")
        mark.optional     = _extract_list(block, "Optional terms")

        # Extract queries from code blocks
        code_blocks = re.findall(r"```(?:sql|text|ansera|pql|)?\n(.*?)\n```", block, re.DOTALL)
        if len(code_blocks) >= 2:
            mark.broad_query = code_blocks[0].strip()
            mark.narrow_query = code_blocks[1].strip()
        elif len(code_blocks) == 1:
            mark.broad_query = code_blocks[0].strip()

        marks.append(mark)

    return marks


def extract_classification_codes(report: str) -> List[str]:
    """Extract IPC/CPC codes from Section 8 table."""
    codes = re.findall(r"\b([A-HY]\d{2}[A-Z]\s*\d+/\d+)\b", report)
    return list(dict.fromkeys(codes))  # deduplicate, preserve order


def extract_boolean_strings(report: str) -> tuple:
    """
    Return (broad_string, narrow_string, mixed_string) from Section 6.
    They are extracted from fenced code blocks in that section.
    """
    section = extract_section(report, "SECTION 6")
    code_blocks = re.findall(r"```(?:sql|text|ansera|pql|)?\n(.*?)\n```", section, re.DOTALL)
    broad  = code_blocks[0].strip() if len(code_blocks) > 0 else ""
    narrow = code_blocks[1].strip() if len(code_blocks) > 1 else ""
    mixed  = code_blocks[2].strip() if len(code_blocks) > 2 else ""
    return broad, narrow, mixed


def parse_full_result(report: str, input_status: InputStatus) -> SearchStrategyResult:
    """
    Parse a raw Markdown report string into a fully populated
    SearchStrategyResult object.
    """
    result = SearchStrategyResult()
    result.full_report   = report
    result.input_status  = input_status

    result.technical_conclusion  = extract_section(report, "SECTION 3")
    result.examiner_notes        = extract_section(report, "SECTION 11")
    result.marks                 = extract_marks(report)
    result.classification_table  = extract_section(report, "SECTION 8")
    result.mixed_search_analysis = extract_section(report, "SECTION 9")
    result.classification_codes  = extract_classification_codes(report)
    result.broad_boolean_string, result.narrow_boolean_string, result.mixed_boolean_string = extract_boolean_strings(report)

    # Search combinations — keep as simple count for now
    n = count_search_combinations(report)
    result.search_combinations = [
        SearchCombination(label=f"Search {i+1}") for i in range(n)
    ]

    if result.num_marks == 0 and result.num_search_combinations == 0:
        result.status = "PARTIAL"
    else:
        result.status = "SUCCESS"

    return result
