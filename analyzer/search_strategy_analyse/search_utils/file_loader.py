"""
file_loader.py — reads the three patent input files and builds the
structured user message that is sent to the LLM alongside the system prompt.

Mirrors the role of guideline_loader.py in claims_utils.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from search_core.search_models import InputStatus


@dataclass
class LoadedDocuments:
    """Raw text content of the three input files."""
    description: Optional[str] = None
    claims:      Optional[str] = None
    drawing:     Optional[str] = None

    @property
    def input_status(self) -> InputStatus:
        return InputStatus(
            description_present=self.description is not None,
            claims_present=self.claims is not None,
            drawing_present=self.drawing is not None,
        )

    def any_present(self) -> bool:
        return any([self.description, self.claims, self.drawing])


class DocumentLoader:
    """
    Reads description.md, claims.md, and drawing.md from a given directory.

    Parameters
    ----------
    input_dir : str or Path
        Path to the folder containing the three input files
        (i.e. analyzer/document_text_output/).
    description_filename : str
    claims_filename : str
    drawing_filename : str
        Filenames for the three documents. Defaults match project conventions.
    """

    def __init__(
        self,
        input_dir: str | Path,
        description_filename: str = "description.md",
        claims_filename:      str = "claims.md",
        drawing_filename:     str = "drawing.md",
    ):
        self.input_dir            = Path(input_dir)
        self.description_filename = description_filename
        self.claims_filename      = claims_filename
        self.drawing_filename     = drawing_filename

    def _read(self, filename: str) -> Optional[str]:
        """Read a single file. Returns None if it does not exist."""
        path = self.input_dir / filename
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8").strip()
        return text if text else None

    def load(self) -> LoadedDocuments:
        """Read all three files and return a LoadedDocuments object."""
        return LoadedDocuments(
            description=self._read(self.description_filename),
            claims=self._read(self.claims_filename),
            drawing=self._read(self.drawing_filename),
        )

    def build_user_message(self, docs: LoadedDocuments) -> str:
        """
        Assemble the user message sent to the LLM.

        Each file is presented as a clearly labelled block so the LLM
        always knows which content comes from which source. Absent files
        are labelled ABSENT so the LLM can note this in Section 1.
        """
        parts = ["## INPUT FILES\n"]

        # Description
        if docs.description:
            parts.append(
                f"### description.md — STATUS: PRESENT\n\n{docs.description}\n"
            )
        else:
            parts.append("### description.md — STATUS: ABSENT\n")

        # Claims
        if docs.claims:
            parts.append(
                f"### claims.md — STATUS: PRESENT\n\n{docs.claims}\n"
            )
        else:
            parts.append("### claims.md — STATUS: ABSENT\n")

        # Drawing
        if docs.drawing:
            parts.append(
                f"### drawing.md — STATUS: PRESENT\n\n{docs.drawing}\n"
            )
        else:
            parts.append("### drawing.md — STATUS: ABSENT\n")

        parts.append(
            "\nNow produce the complete 10-section prior-art search strategy "
            "report as instructed in the system prompt."
        )

        return "\n".join(parts)
