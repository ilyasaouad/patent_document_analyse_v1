import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from backend_extract import MinerUWrapper

def test_extraction():
    wrapper = MinerUWrapper()
    
    test_files = [
        "backend_extract/demo/pdfs/small_ocr.pdf",
        "backend_extract/demo/pdfs/demo1.pdf",
    ]
    
    for file_path in test_files:
        if Path(file_path).exists():
            print(f"\n{'='*50}")
            print(f"Testing: {file_path}")
            print('='*50)
            
            try:
                result = wrapper.extract_text(file_path, document_type="description")
                
                text = result.get("description_text", "")
                if text:
                    print(f"Extracted {len(text)} characters")
                    # Print first 500 chars safely
                    preview = text[:500] if len(text) >= 500 else text
                    print(f"First 500 chars:\n{preview}")
                else:
                    print("No text extracted")
                    
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    test_extraction()
