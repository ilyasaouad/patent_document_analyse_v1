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
from extract_claims_section import ClaimsExtractor

sys.path.insert(0, str(analyzer_dir / "ai_generated_detection"))
from ai_patent_analyzer import AIPatentAnalyzer
from utils.helpers import remove_margin_numbers

sys.path.insert(0, str(analyzer_dir / "claims_analyse"))
from claims_legal_analyzer import PatentLegalAnalyzer

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
# Deep AI Detection is now always enabled automatically.
st.markdown("---")


def clear_folder(folder: Path):
    """Delete all files in a folder, safely jumping over files locked by Windows."""
    for f in folder.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except PermissionError:
                print(f"Warning: Could not delete {f.name} because it is locked by another process (like MS Word).")
            except Exception as e:
                print(f"Warning: Failed to delete {f.name}: {e}")


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


def save_to_output_dir(text: str, file_name: str) -> Path:
    """
    Save extracted text to analyzer/document_text_output/
    with the given file_name.
    """
    output_path = OUTPUT_DIR / file_name
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
                
                # Physically clean margin numbers out of the string BEFORE saving files
                if desc_text:
                    desc_text = remove_margin_numbers(desc_text)
                if claims_text:
                    claims_text = remove_margin_numbers(claims_text)

                # ── Step 3: Save extracted text to document_text_output as .md ──
                desc_output = save_to_output_dir(desc_text, "description.md") if desc_text else None
                claims_output = save_to_output_dir(claims_text, "claims.md") if claims_text else None
                drawings_output = save_to_output_dir(drawings_text, "drawings.md") if drawings_text else None

                # ── Step 3.5: Post-Processing & Auto-Extract Claims ──
                try:
                    extractor = ClaimsExtractor(input_dir=str(OUTPUT_DIR))
                except Exception as analyzer_e:
                    st.warning(f"Claims Extractor encountered an error: {analyzer_e}")

                extracted_claims_path = OUTPUT_DIR / "claims_from_description.md"
                extracted_claims_text = ""
                if extracted_claims_path.exists():
                    with open(extracted_claims_path, "r", encoding="utf-8") as f:
                        extracted_claims_text = f.read()
                        
                desc_only_path = OUTPUT_DIR / "description_only.md"
                if desc_only_path.exists():
                    with open(desc_only_path, "r", encoding="utf-8") as f:
                        desc_text = f.read()

                # ── Step 3.6: Deep AI Detection ──
                ai_result = None
                try:
                    with st.spinner("🤖 Running Deep AI Detection (This can take a few minutes on local LLMs)..."):
                        # Use the new modular AI Patent Analyzer
                        ai_analyzer = AIPatentAnalyzer(input_dir=str(OUTPUT_DIR))
                        ai_result = ai_analyzer.run_analysis()
                except Exception as ai_e:
                    st.warning(f"AI Detection encountered an error: {ai_e}")

                # ── Step 3.7: Legal Analysis (EPO/NIPO) ──
                legal_result = None
                try:
                    with st.spinner("⚖️ Running Patent Legal Analysis (EPO/NIPO standards)..."):
                        legal_analyzer = PatentLegalAnalyzer()
                        
                        claims_to_analyze = claims_text if claims_text else extracted_claims_text
                        if claims_to_analyze and desc_text:
                            legal_result = legal_analyzer.analyze(
                                claims=claims_to_analyze,
                                description=desc_text,
                                drawings=drawings_text if drawings_text else None
                            )
                        else:
                            st.warning("Legal analysis skipped: Requires both claims and description text.")
                except Exception as legal_e:
                    st.warning(f"Legal Analysis encountered an error: {legal_e}")

                # ── Step 4: Show results ──
                st.success("✅ Extraction & Processing Complete!")
                
                # Proactive Drawing Warning
                if not drawings_text and desc_text:
                    import re
                    drawing_patterns = r'(?i)(brief description of the drawings?|accompanying drawings?|referring to figure|shown in fig|figur\s+\d+|fig\.\s*\d+|tegning\s+\d+|vist i figur)'
                    if re.search(drawing_patterns, desc_text):
                        st.warning("⚠️ **Notice:** Your description explicitly references drawings (like 'Fig. 1' or 'Tegning'), but no Drawing file was uploaded! You might want to upload it for a more complete analysis.")

                st.markdown("**📂 Input documents saved to:**")
                input_files = [f for f in INPUT_DIR.iterdir() if f.is_file()]
                st.code("\n".join([f"  {f.name}" for f in input_files]))

                st.markdown("**📄 Output text saved to:**")
                output_files = [f for f in OUTPUT_DIR.iterdir() if f.is_file()]
                st.code("\n".join([f"  {f.name}" for f in output_files]))

                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📑 Description", "⚖️ Claims", "🖼️ Drawings", "🔍 Extracted Claims", "🤖 AI Analysis", "⚖️ Legal Analysis"])

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
                        
                with tab4:
                    if extracted_claims_text:
                        st.text_area("Claims (Auto-Extracted definitively)", value=extracted_claims_text, height=500)
                    else:
                        st.info("No claims were algorithmically detected in the description.")
                        
                with tab5:
                    if ai_result:
                        if ai_result.risk_level == "ERROR":
                            st.error(f"AI Detection failed. Make sure documents were properly extracted.")
                        else:
                            st.subheader("📊 AI Detection Result")
                            colA, colB = st.columns(2)
                            with colA:
                                st.metric("AI Generated", "YES ⚠️" if ai_result.is_likely_ai_generated else "NO ✓")
                                st.metric("Risk Level", ai_result.risk_level)
                            with colB:
                                st.metric("Confidence Score", f"{ai_result.confidence_score:.1%}")
                                st.metric("Main Driver", "Anchor Comparison")
                            
                            st.markdown("### 📋 Recommendations")
                            for rec in ai_result.recommendations:
                                st.markdown(f"- {rec}")
                            
                            st.markdown("### 📈 Feature Scores")    
                            st.json(ai_result.feature_scores)
                                
                            st.markdown("### 🔍 Detailed Analysis")
                            with st.expander("View Raw JSON Metrics"):
                                st.json(ai_result.detailed_analysis)
                    else:
                        st.warning("No result produced by AI Analyzer.")

                with tab6:
                    if legal_result:
                        st.subheader("⚖️ Legal Examination Decision")
                        
                        if legal_result.examination_decision == "GRANT":
                            st.success(f"## {legal_result.examination_decision}")
                        elif legal_result.examination_decision == "OBJECT":
                            st.error(f"## {legal_result.examination_decision}")
                        else:
                            st.warning(f"## {legal_result.examination_decision}")
                            
                        st.markdown(f"**Risk Level:** {legal_result.risk_level}")
                        st.markdown(f"_{legal_result.summary}_")
                        
                        st.markdown("---")
                        colA, colB, colC = st.columns(3)
                        
                        with colA:
                            st.metric("Enablement (Art. 83)", "✓ PASS" if legal_result.enablement.status == "ENABLED" else "❌ FAIL")
                        with colB:
                            st.metric("Clarity (Art. 84)", "✓ PASS" if legal_result.clarity.status == "CLEAR" else "❌ FAIL")
                        with colC:
                            st.metric("Support (Art. 84)", "✓ PASS" if legal_result.support.status == "SUPPORTED" else "❌ FAIL")
                            
                        if legal_result.critical_issues:
                            st.error("**Critical Issues:**\n" + "\n".join([f"- {i}" for i in legal_result.critical_issues]))
                            
                        st.markdown("### Recommendations")
                        for rec in legal_result.recommendations:
                            st.markdown(f"- {rec}")
                            
                        with st.expander("View Full Detailed Report"):
                            st.text(legal_result.get_summary_report())
                            st.markdown("**Raw JSON Data:**")
                            st.json(legal_result.to_dict())
                    else:
                        st.warning("No result produced by Patent Legal Analyzer.")

            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.caption("Patent Document Analyser v1.0 | Powered by MinerU OCR")
