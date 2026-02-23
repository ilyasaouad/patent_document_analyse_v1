"""
Streamlit Frontend for Patent Document Text Extract Service.
Upload description, claims, and drawing documents for text extraction.
"""

import streamlit as st
import requests
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Patent Document Extractor", page_icon="📄", layout="wide"
)

st.title("📄 Patent Document Text Extractor")

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
        "Drawings PDF (optional)", type=["pdf"], key="drawings"
    )

st.markdown("---")

if st.button("🚀 Extract Text", type="primary", use_container_width=True):
    if not desc_file:
        st.error("Please upload a Description document (required)")
    else:
        with st.spinner("Extracting text..."):
            files = {
                "description_file": (
                    desc_file.name,
                    desc_file.getvalue(),
                    desc_file.type,
                )
            }

            if claims_file:
                files["claims_file"] = (
                    claims_file.name,
                    claims_file.getvalue(),
                    claims_file.type,
                )

            if drawings_file:
                files["drawings_file"] = (
                    drawings_file.name,
                    drawings_file.getvalue(),
                    drawings_file.type,
                )

            try:
                response = requests.post(
                    f"{API_BASE_URL}/extract/all", files=files, timeout=300
                )

                if response.status_code == 200:
                    result = response.json()

                    st.success("✅ Extraction Complete!")

                    tab1, tab2, tab3, tab4 = st.tabs(
                        ["📑 Description", "⚖️ Claims", "🖼️ Drawings", "📝 Abstract"]
                    )

                    with tab1:
                        if result.get("description_text"):
                            st.text_area(
                                "Description Text",
                                value=result["description_text"],
                                height=500,
                            )
                        else:
                            st.warning("No description text extracted")

                    with tab2:
                        if result.get("claims_text"):
                            st.text_area(
                                "Claims Text", value=result["claims_text"], height=500
                            )
                        else:
                            st.info("No claims file was provided")

                    with tab3:
                        if result.get("drawings_text"):
                            st.text_area(
                                "Drawings Text",
                                value=result["drawings_text"],
                                height=500,
                            )
                        else:
                            st.info("No drawings file was provided")

                    with tab4:
                        if result.get("abstract_text"):
                            st.text_area(
                                "Abstract", value=result["abstract_text"], height=200
                            )
                        else:
                            st.info("No abstract found in document")

                else:
                    st.error(f"Error: {response.status_code}")
                    st.text(response.text)

            except requests.exceptions.ConnectionError:
                st.error(
                    f"Cannot connect to API at {API_BASE_URL}. Make sure the FastAPI server is running."
                )
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.caption("Patent Document Text Extractor v1.0 | Powered by MinerU OCR")
