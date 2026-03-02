"""
Streamlit Frontend for Patent Document Analyse Service.

Upload description, claims, and drawing documents for text extraction.

Workflow:
  1. User uploads documents → saved to analyzer/document_original_input/
  2. Backend extracts text via MinerU
  3. Extracted text saved to analyzer/document_text_output/ as .md files
  4. backend_extract acts purely as a backend server
"""

import sys
import os
import shutil
from pathlib import Path

os.environ['MINERU_MODEL_SOURCE'] = 'local'

project_root = Path(__file__).parent.parent.absolute()
analyzer_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend_extract"))
os.chdir(project_root)

# Create input/output directories
INPUT_DIR = analyzer_dir / "document_original_input"
OUTPUT_DIR = analyzer_dir / "document_text_output"
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

import streamlit as st
from backend_extract import MinerUWrapper

st.set_page_config(
    page_title="Patent Document Extractor", page_icon="📄", layout="wide"
)

st.title("📄 Patent Document Analyser")

st.markdown("Upload your patent documents to extract text using MinerU OCR.")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📑 Description")
    desc_file = st.file_uploader(
        "Description PDF/DOCX", type=["pdf", "docx"], key="desc"
    )

with col2:
    st.subheader("⚖️ Claims")
    claims_file = st.file_uploader(
        "Claims PDF/DOCX (optional)", type=["pdf", "docx"], key="claims"
    )

with col3:
    st.subheader("🖼️ Drawings")
    drawings_file = st.file_uploader(
        "Drawings PDF/DOCX (optional)", type=["pdf", "docx"], key="drawings"
    )

st.markdown("---")


def clear_folder(folder: Path):
    """Delete all files in a folder."""
    for f in folder.iterdir():
        if f.is_file():
            f.unlink()


def save_to_input_dir(upload_file) -> Path:
    """
    Save uploaded file to analyzer/document_original_input/
    using its original file name.
    """
    if not upload_file:
        return None

    saved_path = INPUT_DIR / upload_file.name

    with open(saved_path, "wb") as f:
        f.write(upload_file.getvalue())

    return saved_path


def save_to_output_dir(text: str, original_name: str) -> Path:
    """
    Save extracted text to analyzer/document_text_output/
    as a .md file using the original file name (with .md extension).
    """
    stem = Path(original_name).stem  # e.g. 'Besk_Patent_2025'
    output_path = OUTPUT_DIR / f"{stem}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return output_path


if st.button("🚀 Extract Text", type="primary", use_container_width=True):
    if not desc_file:
        st.error("Please upload a Description document (required)")
    else:
        with st.spinner("Extracting text..."):

            # ── Clear old files from both folders ──
            clear_folder(INPUT_DIR)
            clear_folder(OUTPUT_DIR)

            # ── Step 1: Save original uploads to document_original_input ──
            desc_path = save_to_input_dir(desc_file)
            claims_path = save_to_input_dir(claims_file) if claims_file else None
            drawings_path = save_to_input_dir(drawings_file) if drawings_file else None

            try:
                # ── Step 2: Send to backend_extract for processing ──
                wrapper = MinerUWrapper()
                result = wrapper.extract_all(
                    description_path=str(desc_path),
                    claims_path=str(claims_path) if claims_path else None,
                    drawings_path=str(drawings_path) if drawings_path else None,
                )

                desc_text = result.get("description_text", "")
                claims_text = result.get("claims_text", "")
                drawings_text = result.get("drawings_text", "")

                # ── Step 3: Save extracted text to document_text_output as .md ──
                desc_output = save_to_output_dir(desc_text, desc_file.name) if desc_text else None
                claims_output = save_to_output_dir(claims_text, claims_file.name) if claims_text else None
                drawings_output = save_to_output_dir(drawings_text, drawings_file.name) if drawings_text else None

                # ── Step 4: Show results ──
                st.success("✅ Extraction Complete!")

                st.markdown("**📂 Input documents saved to:**")
                input_files = [f for f in INPUT_DIR.iterdir() if f.is_file()]
                st.code("\n".join([f"  {f.name}" for f in input_files]))

                st.markdown("**📄 Output text saved to:**")
                output_files = [f for f in OUTPUT_DIR.iterdir() if f.is_file()]
                st.code("\n".join([f"  {f.name}" for f in output_files]))

                tab1, tab2, tab3 = st.tabs(["📑 Description", "⚖️ Claims", "🖼️ Drawings"])

                with tab1:
                    if desc_text:
                        st.text_area("Description Text", value=desc_text, height=500)
                    else:
                        st.warning("No description text extracted")

                with tab2:
                    if claims_text:
                        st.text_area("Claims Text", value=claims_text, height=500)
                    else:
                        st.info("No claims file was provided")

                with tab3:
                    if drawings_text:
                        st.text_area("Drawings Text", value=drawings_text, height=500)
                    else:
                        st.info("No drawings file was provided")

            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.caption("Patent Document Analyser v1.0 | Powered by MinerU OCR")
