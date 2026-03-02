"""
Image OCR - Handles OCR extraction from images.
"""

from pathlib import Path
from typing import Optional


class ImageOCR:
    """
    Performs OCR on image files (PNG, JPG, TIFF, BMP).
    """

    def __init__(self, lang: str = "en"):
        self.lang = lang

    def extract_text(self, file_path: str, lang: Optional[str] = None) -> str:
        """
        Extract text from image using OCR.

        Args:
            file_path: Path to image file
            lang: Language code (overrides instance default)

        Returns:
            Extracted text
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {file_path}")

        language = lang or self.lang
        return self._ocr_image(path, language)

    def _ocr_image(self, path: Path, lang: str) -> str:
        """Perform OCR on image."""
        try:
            import pytesseract
            from PIL import Image
            from backend_extract.docx_image_ocr import _find_tesseract

            tesseract_cmd = _find_tesseract()
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            # Map MinerU's 'en' language code to Tesseract's 'eng' language code
            tesseract_lang = "eng" if lang == "en" else lang
            
            image = Image.open(path)
            # Use PSM 11 (Sparse text, find as much text as possible in no particular order)
            # This is critical for patent drawings where labels are scattered
            raw_text = pytesseract.image_to_string(image, lang=tesseract_lang, config="--psm 11")
            
            # Clean the raw text using the drawing-specific cleaner
            from .text_cleaning import full_clean_patent_text
            import re
            
            lines = raw_text.split('\n')
            kept_lines = []
            seen_content = set()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                keep = False
                # Keep if has digit (good for reference numerals) or looks like a short label
                if re.search(r'\d', line) or len(line) < 60:
                    keep = True
                    
                if keep:
                    norm_line = re.sub(r'\s+', ' ', line.lower())
                    if norm_line not in seen_content:
                        seen_content.add(norm_line)
                        kept_lines.append(line)
                        
            cleaned_text = '\n'.join(kept_lines)
            return full_clean_patent_text(cleaned_text)
        except ImportError:
            raise ImportError("pytesseract or Pillow not installed")

    def extract_with_layout(self, file_path: str) -> dict:
        """
        Extract text with layout information (bounding boxes).

        Returns:
            Dict with boxes, confidences, and text
        """
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(file_path)
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            return data
        except ImportError:
            raise ImportError("pytesseract not installed")
