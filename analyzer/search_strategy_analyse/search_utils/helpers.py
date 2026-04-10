"""
helpers.py — utilities for parsing and extracting content from the
generated Markdown search strategy report.

Mirrors claims_utils/helpers.py in structure.
"""

import re
from typing import List, Tuple


def extract_section(report: str, section_keyword: str) -> str:
    """
    Extract the body text of a Markdown section identified by a keyword
    in the heading. Stops at the next heading of equal or higher level (##).

    Parameters
    ----------
    report : str
        Full Markdown report text.
    section_keyword : str
        A keyword that uniquely identifies the target section heading,
        e.g. "SECTION 3", "SECTION 6", "EXAMINER NOTES".

    Returns
    -------
    str
        The body text of the section, stripped of leading/trailing whitespace.
        Empty string if the section is not found.
    """
    lines = report.splitlines()
    in_section = False
    collected: List[str] = []

    for line in lines:
        stripped = line.strip()

        is_heading = stripped.startswith("#")
        if is_heading and section_keyword.lower() in stripped.lower():
            in_section = True
            continue

        if in_section:
            # Stop at any ## or # heading
            if re.match(r"^#{1,2}\s", stripped):
                break
            collected.append(line)

    return "\n".join(collected).strip()


def count_marks(report: str) -> int:
    """
    Count how many Mark sections appear in the report.

    Looks for headings of the form:
        ### Mark A — Concept Name
        ## Mark B — Another Concept
    """
    return len(re.findall(r"(?im)^#+\s+Mark\s+[A-Z]\b", report))


def count_search_combinations(report: str) -> int:
    """
    Count numbered search combinations in Section 5.

    Looks for bullet lines of the form:
        - Search 1 (broad): ...
        * Search 2 ...
    """
    return len(re.findall(r"(?im)^[-*]\s+Search\s+\d+", report))


def extract_classification_codes(report: str) -> List[str]:
    """
    Extract IPC / CPC classification codes from the report.

    Matches patterns like:  G06N 3/00   H03M 1/10   G06F 15/78
    Deduplicates while preserving order of first occurrence.
    """
    raw = re.findall(r"\b([A-HY]\d{2}[A-Z]\s*\d+/\d+)\b", report)
    seen = set()
    unique = []
    for code in raw:
        normalised = re.sub(r"\s+", " ", code).strip()
        if normalised not in seen:
            seen.add(normalised)
            unique.append(normalised)
    return unique


def extract_boolean_strings(report: str) -> Tuple[str, str]:
    """
    Extract the broad and narrow ANSERA boolean strings from Section 6.

    Looks for fenced code blocks (``` ... ```) within Section 6.
    Returns a tuple: (broad_string, narrow_string).
    Either value may be an empty string if not found.
    """
    section = extract_section(report, "SECTION 6")
    code_blocks = re.findall(
        r"```(?:sql|text|ansera|ansera-search|)?\n(.*?)\n```",
        section,
        re.DOTALL,
    )
    broad  = code_blocks[0].strip() if len(code_blocks) > 0 else ""
    narrow = code_blocks[1].strip() if len(code_blocks) > 1 else ""
    return broad, narrow


def extract_mark_table_rows(report: str) -> List[dict]:
    """
    Parse the Markdown table in Section 7 into a list of dicts.

    Each dict has keys: mark, concept, broad, narrow, must_have, optional.
    Returns an empty list if the table cannot be parsed.
    """
    section = extract_section(report, "SECTION 7")
    rows = []

    lines = [l.strip() for l in section.splitlines() if l.strip().startswith("|")]
    # Skip header and separator rows
    data_lines = [l for l in lines if not re.match(r"^\|[-| ]+\|$", l)]
    if data_lines and "Mark" in data_lines[0]:
        data_lines = data_lines[1:]  # skip header row

    for line in data_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 6:
            rows.append({
                "mark":      cells[0],
                "concept":   cells[1],
                "broad":     cells[2],
                "narrow":    cells[3],
                "must_have": cells[4],
                "optional":  cells[5],
            })

    return rows


def truncate_for_display(text: str, max_chars: int = 300) -> str:
    """Truncate text for UI display with ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"
