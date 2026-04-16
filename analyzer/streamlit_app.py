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

os.environ['MINERU_MODEL_SOURCE'] = 'huggingface'

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

sys.path.insert(0, str(analyzer_dir / "search_strategy_analyse"))
from search_strategy_analyzer import SearchStrategyAnalyzer

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
                legal_client = None
                try:
                    claims_to_analyze = claims_text if claims_text else extracted_claims_text
                    if claims_to_analyze and desc_text:
                        with st.spinner("⚖️ Running Patent Legal Analysis (gpt-oss:120b-cloud)..."):
                            from claims_core import OllamaClient
                            legal_client = OllamaClient(model_name="gpt-oss:120b-cloud")
                            legal_analyzer = PatentLegalAnalyzer(ollama_client=legal_client)
                            
                            legal_result = legal_analyzer.analyze(
                                claims=claims_to_analyze,
                                description=desc_text,
                                drawings=drawings_text if drawings_text else None
                            )
                            
                            # Save the legal analysis report
                            analyse_dir = Path(__file__).resolve().parent / "claims_analyse" / "analyse_result"
                            analyse_dir.mkdir(parents=True, exist_ok=True)
                            report_path = analyse_dir / "legal_analysis_report.md"
                            with open(report_path, "w", encoding="utf-8") as f:
                                f.write(legal_result.get_summary_report())
                                
                    else:
                        st.warning("Legal analysis skipped: Requires both claims and description text.")
                except Exception as legal_e:
                    st.warning(f"Legal Analysis encountered an error: {legal_e}")

                # ── Step 3.8: Search Strategy Analysis ──
                search_result = None
                search_client = None
                try:
                    claims_to_analyze = claims_text if claims_text else extracted_claims_text
                    if claims_to_analyze and desc_text:
                        with st.spinner("🔎 Running Search Strategy Analysis (gpt-oss:120b-cloud)..."):
                            from search_core.ollama_client import OllamaClient as SearchOllamaClient
                            search_client = SearchOllamaClient(model_name="gpt-oss:120b-cloud")
                            search_analyzer = SearchStrategyAnalyzer(
                                ollama_client=search_client,
                                input_dir=str(OUTPUT_DIR),
                            )
                            search_result = search_analyzer.analyze()
                    else:
                        st.warning("Search Strategy skipped: Requires both claims and description text.")
                except Exception as search_e:
                    st.warning(f"Search Strategy Analysis encountered an error: {search_e}")

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

                tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📑 Description", "⚖️ Claims", "🖼️ Drawings", "🔍 Extracted Claims", "🤖 AI Analysis", "⚖️ Legal Analysis", "🔎 Search Strategy", "📊 LLM Usage"])

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
                            
                        # Formal Report Rendering
                        st.markdown("---")
                        st.markdown("### 📝 Formal Examination Report")
                        if legal_result.formal_report:
                            st.info(legal_result.formal_report)
                        else:
                            st.warning("Formal report not generated.")
                        st.markdown("---")
                            
                        st.markdown(f"**Risk Level:** {legal_result.risk_level}")
                        st.markdown(f"_{legal_result.summary}_")
                        
                        st.markdown("---")
                        colA, colB, colC = st.columns(3)
                        
                        with colA:
                            st.metric("Enablement", "✓ PASS" if legal_result.enablement.status == "ENABLED" else "❌ FAIL")
                        with colB:
                            st.metric("Clarity", "✓ PASS" if legal_result.clarity.status == "CLEAR" else "❌ FAIL")
                        with colC:
                            st.metric("Support", "✓ PASS" if legal_result.support.status == "SUPPORTED" else "❌ FAIL")
                            
                        if legal_result.critical_issues:
                            st.error("**Critical Issues:**\n" + "\n".join([f"- {iss}" for iss in legal_result.critical_issues]))
                            
                        st.markdown("#### Recommendations")
                        for rec in legal_result.recommendations:
                            st.markdown(f"- {rec}")
                            
                        with st.expander("View Full Detailed Report", expanded=False):
                            st.text(legal_result.get_summary_report())
                            st.markdown("**Raw JSON Data:**")
                            st.json(legal_result.to_dict())
                    else:
                        st.warning("No result produced by Patent Legal Analyzer.")

                with tab7:
                    if search_result:
                        if search_result.status == "ERROR":
                            st.error(f"Search Strategy Analysis failed: {search_result.error_message}")
                        else:
                            st.subheader("🔎 Search Strategy Report")
                            
                            # Status badge
                            if search_result.status == "SUCCESS":
                                st.success(f"## Status: {search_result.status}")
                            else:
                                st.warning(f"## Status: {search_result.status}")
                            
                            # Key metrics
                            st.markdown("---")
                            colA, colB, colC = st.columns(3)
                            with colA:
                                st.metric("Marks Identified", search_result.num_marks)
                            with colB:
                                st.metric("Search Combinations", search_result.num_search_combinations)
                            with colC:
                                st.metric("IPC/CPC Codes", len(search_result.classification_codes))
                            
                            # Input file status
                            st.markdown("---")
                            st.markdown("#### 📂 Input Files")
                            st.code(search_result.input_status.summary())
                            
                            # Technical Conclusion
                            if search_result.technical_conclusion:
                                st.markdown("#### 🧪 Technical Conclusion")
                                st.info(search_result.technical_conclusion)
                            
                            # Marks
                            if search_result.marks:
                                st.markdown("#### 🏷️ Keyword Marks")
                                for mark in search_result.marks:
                                    with st.expander(f"Mark {mark.label} — {mark.concept}", expanded=False):
                                        if mark.broad_terms:
                                            st.markdown("**Broad terms:** " + ", ".join(mark.broad_terms))
                                        if mark.narrow_terms:
                                            st.markdown("**Narrow terms:** " + ", ".join(mark.narrow_terms))
                                        if mark.must_have:
                                            st.markdown("**Must-have:** " + ", ".join(mark.must_have))
                                        if mark.optional:
                                            st.markdown("**Optional:** " + ", ".join(mark.optional))
                                        if mark.proximity_example:
                                            st.code(mark.proximity_example)
                            
                            # Boolean strings
                            if search_result.broad_boolean_string or search_result.narrow_boolean_string:
                                st.markdown("#### 🔗 Boolean Search Strings")
                                if search_result.broad_boolean_string:
                                    st.markdown("**Broad:**")
                                    st.code(search_result.broad_boolean_string, language="sql")
                                if search_result.narrow_boolean_string:
                                    st.markdown("**Narrow:**")
                                    st.code(search_result.narrow_boolean_string, language="sql")
                            
                            # Classification codes
                            if search_result.classification_codes:
                                st.markdown("#### 📋 Classification Codes")
                                st.markdown(", ".join([f"`{c}`" for c in search_result.classification_codes]))
                            
                            # Examiner notes
                            if search_result.examiner_notes:
                                st.markdown("#### 📝 Examiner Notes")
                                st.info(search_result.examiner_notes)
                            
                            # Full report
                            with st.expander("View Full Search Strategy Report", expanded=False):
                                st.markdown(search_result.full_report)
                                st.markdown("**Raw JSON Data:**")
                                st.json(search_result.to_dict())
                    else:
                        st.warning("No result produced by Search Strategy Analyzer.")

                with tab8:
                    st.subheader("📊 LLM Token Usage & Cost Estimation")
                    st.markdown("_Token counts from Ollama API. Cost estimates based on **OpenAI GPT-4.1** pricing._")
                    
                    # OpenAI GPT-4.1 pricing (per 1M tokens)
                    INPUT_COST_PER_M  = 2.00   # $2.00 per 1M input tokens
                    OUTPUT_COST_PER_M = 8.00   # $8.00 per 1M output tokens
                    
                    # Collect usage from both clients
                    usage_rows = []
                    total_prompt = 0
                    total_completion = 0
                    total_duration_s = 0.0
                    
                    if legal_client:
                        u = legal_client.usage
                        dur_s = u["total_duration_ns"] / 1e9
                        usage_rows.append({
                            "Module": "⚖️ Legal Analysis",
                            "API Calls": u["calls"],
                            "Prompt Tokens": f"{u['prompt_tokens']:,}",
                            "Completion Tokens": f"{u['completion_tokens']:,}",
                            "Total Tokens": f"{u['total_tokens']:,}",
                            "Duration (s)": f"{dur_s:.1f}",
                        })
                        total_prompt += u["prompt_tokens"]
                        total_completion += u["completion_tokens"]
                        total_duration_s += dur_s
                    
                    if search_client:
                        u = search_client.usage
                        dur_s = u["total_duration_ns"] / 1e9
                        usage_rows.append({
                            "Module": "🔎 Search Strategy",
                            "API Calls": u["calls"],
                            "Prompt Tokens": f"{u['prompt_tokens']:,}",
                            "Completion Tokens": f"{u['completion_tokens']:,}",
                            "Total Tokens": f"{u['total_tokens']:,}",
                            "Duration (s)": f"{dur_s:.1f}",
                        })
                        total_prompt += u["prompt_tokens"]
                        total_completion += u["completion_tokens"]
                        total_duration_s += dur_s
                    
                    total_all = total_prompt + total_completion
                    
                    if usage_rows:
                        # Summary metrics
                        colA, colB, colC, colD = st.columns(4)
                        with colA:
                            st.metric("Total Prompt Tokens", f"{total_prompt:,}")
                        with colB:
                            st.metric("Total Completion Tokens", f"{total_completion:,}")
                        with colC:
                            st.metric("Total Tokens", f"{total_all:,}")
                        with colD:
                            st.metric("Total Duration", f"{total_duration_s:.1f}s")
                        
                        st.markdown("---")
                        
                        # Per-module breakdown table
                        st.markdown("#### 📋 Per-Module Breakdown")
                        import pandas as pd
                        df = pd.DataFrame(usage_rows)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        st.markdown("---")
                        
                        # Cost estimation
                        st.markdown("#### 💰 Estimated Cost (if using OpenAI GPT-4.1)")
                        st.caption("Pricing: Input $2.00/1M tokens · Output $8.00/1M tokens · [openai.com/api/pricing](https://openai.com/api/pricing)")
                        
                        input_cost  = (total_prompt / 1_000_000) * INPUT_COST_PER_M
                        output_cost = (total_completion / 1_000_000) * OUTPUT_COST_PER_M
                        total_cost  = input_cost + output_cost
                        
                        colX, colY, colZ = st.columns(3)
                        with colX:
                            st.metric("Input Cost", f"${input_cost:.4f}")
                        with colY:
                            st.metric("Output Cost", f"${output_cost:.4f}")
                        with colZ:
                            st.metric("Total Estimated Cost", f"${total_cost:.4f}")
                        
                        # Cost context
                        st.markdown("---")
                        st.markdown("#### 📈 Cost at Scale")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Per 10 Patents", f"${total_cost * 10:.2f}")
                        with col2:
                            st.metric("Per 100 Patents", f"${total_cost * 100:.2f}")
                        with col3:
                            st.metric("Per 1,000 Patents", f"${total_cost * 1000:.2f}")
                        
                        st.success("✅ You are currently using a **local LLM** via Ollama — actual cost: **$0.00**")
                    else:
                        st.info("No LLM calls were made during this analysis session.")

            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.caption("Patent Document Analyser v1.0 | Powered by MinerU OCR")
