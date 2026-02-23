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

            image = Image.open(path)
            return pytesseract.image_to_string(image, lang=lang)
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
