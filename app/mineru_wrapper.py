"""
MinerU Wrapper - Wraps MinerU for patent document text extraction.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional

os.environ["MINERU_MODEL_SOURCE"] = "modelscope"

MODULE_ROOT = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(MODULE_ROOT))


try:
    from demo.demo import parse_doc

    MINERU_AVAILABLE = True
except ImportError as e:
    MINERU_AVAILABLE = False
    print(f"[MinerUWrapper] MinerU not available: {e}")
    print("[MinerUWrapper] Using pypdf fallback for PDF extraction")


class MinerUWrapper:
    """
    Wrapper class for MinerU document extraction.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or tempfile.gettempdir()
        self.mineru_available = MINERU_AVAILABLE

    @staticmethod
    def is_available() -> bool:
        return MINERU_AVAILABLE

    def extract_text(
        self, file_path: str, document_type: str = "description"
    ) -> Dict[str, str]:
        """
        Extract text from a single document.

        Args:
            file_path: Path to the document (PDF, DOCX, image)
            document_type: "description", "claims", or "drawings"

        Returns:
            Dict with extracted text
        """
        

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        if ext == ".pdf":
            text = self._process_pdf(path)
        elif ext == ".docx":
            text = self._process_docx(path)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            text = self._process_image(path)
        else:
            raise ValueError(f"Unsupported format: {ext}")

        result = {"description_text": text}

        if document_type == "description":
            result.update(self._split_sections(text))

        return result

    def extract_all(
        self,
        description_path: Optional[str] = None,
        claims_path: Optional[str] = None,
        drawings_path: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Extract text from all document types.

        Args:
            description_path: Path to description PDF
            claims_path: Path to claims PDF
            drawings_path: Path to drawings PDF

        Returns:
            Dict with all extracted texts
        """
        result = {
            "description_text": None,
            "claims_text": None,
            "abstract_text": None,
            "drawings_text": None,
        }

        if description_path:
            desc_result = self.extract_text(description_path, "description")
            result["description_text"] = desc_result.get("description_text")
            result["abstract_text"] = desc_result.get("abstract_text")

        if claims_path:
            claims_result = self.extract_text(claims_path, "claims")
            result["claims_text"] = claims_result.get("description_text")

        if drawings_path:
            drawings_result = self.extract_text(drawings_path, "drawings")
            result["drawings_text"] = drawings_result.get("description_text")

        return result

    def _process_pdf(self, path: Path) -> str:
        """Process PDF using MinerU or fallback to pypdf."""
        if MINERU_AVAILABLE:
            run_output = tempfile.mkdtemp(prefix="mineru_output_", dir=self.output_dir)

            parse_doc(
                path_list=[path],
                output_dir=run_output,
                lang="en",
                backend="pipeline",
                method="auto",
                formula_enable=False,
                table_enable=True,
            )

            for root, _, files in os.walk(run_output):
                for f in files:
                    if f.endswith(".md") and not f.endswith("_layout.md"):
                        res_path = os.path.join(root, f)
                        with open(res_path, "r", encoding="utf-8") as fh:
                            return fh.read()

            raise RuntimeError(f"No Markdown output found in {run_output}")
        else:
            return self._process_pdf_pypdf(path)

    def _process_pdf_pypdf(self, path: Path) -> str:
        """Fallback PDF extraction using pypdf."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("pypdf is required for PDF extraction. Install with: pip install pypdf")

        reader = PdfReader(str(path))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n".join(text_parts)

    def _process_docx(self, path: Path) -> str:
        """Process DOCX file by converting to PDF first."""
        try:
            import tempfile
            from docx2pdf import convert
            
            pdf_path = path.with_suffix(".pdf")
            convert(str(path), str(pdf_path))
            
            if pdf_path.exists():
                text = self._process_pdf(pdf_path)
                pdf_path.unlink()
                return text
            
            raise RuntimeError("PDF conversion failed")
        except Exception as e:
            raise RuntimeError(f"DOCX extraction failed: {e}")

    def _process_image(self, path: Path) -> str:
        """Process image file using OCR."""
        try:
            from app.image_ocr import ImageOCR

            ocr = ImageOCR()
            return ocr.extract_text(path)
        except ImportError as e:
            raise RuntimeError(f"Image OCR failed: {e}")

    def _split_sections(self, text: str) -> Dict[str, str]:
        """
        Split text into description, claims, and abstract sections.
        Uses regex patterns to find section headers.
        """
        import re

        result = {"description_text": text, "claims_text": None, "abstract_text": None}

        claims_pattern = re.compile(
            r"(?im)(^\s*\d+[\.\)]?\s*claims?\s*$|^\s*claims?\s*$|^\s*what\s+is\s+claimed)",
            re.MULTILINE,
        )

        abstract_pattern = re.compile(
            r"(?im)(^\s*\d+[\.\)]?\s*abstract\s*$|^\s*abstract\s*$)", re.MULTILINE
        )

        claims_match = claims_pattern.search(text)
        if claims_match:
            result["description_text"] = text[: claims_match.start()].strip()
            result["claims_text"] = text[claims_match.start() :].strip()

            abstract_match = abstract_pattern.search(result["claims_text"])
            if abstract_match:
                result["claims_text"] = result["claims_text"][
                    : abstract_match.start()
                ].strip()
                result["abstract_text"] = result["claims_text"][
                    abstract_match.end() :
                ].strip()
        else:
            abstract_match = abstract_pattern.search(text)
            if abstract_match:
                result["description_text"] = text[: abstract_match.start()].strip()
                result["abstract_text"] = text[abstract_match.end() :].strip()

        return result
