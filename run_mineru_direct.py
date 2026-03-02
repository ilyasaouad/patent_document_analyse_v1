import os
import sys
from pathlib import Path

# Add backend_extract to path so we can find 'mineru'
sys.path.append(os.path.join(os.getcwd(), 'backend_extract'))

from backend_extract.demo.demo import parse_doc

# 1. Define the PDF to process
pdf_path = Path(r"C:\Users\iao\Desktop\Beskrivelse\Besk_Encoded_2025_0104.pdf")
output_dir = Path(r"C:\Users\iao\Desktop\MinerU_Test_Output")

# Ensure output directory exists
if not output_dir.exists():
    output_dir.mkdir(parents=True)

print(f"Starting MinerU extraction for: {pdf_path}")
print(f"Results will be saved in: {output_dir}")

# 2. Run the extraction
# We use 'hybrid-auto-engine' as it's typically the best balance
parse_doc(
    path_list=[pdf_path],
    output_dir=str(output_dir),
    lang="en", # Default to English, change to 'ch' for Chinese
    backend="pipeline", # 'pipeline' is often more compatible for general setups
    method="auto"
)

print("Done! Check the output folder on your desktop.")
