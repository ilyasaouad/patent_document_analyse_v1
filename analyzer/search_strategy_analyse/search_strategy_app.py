"""
Streamlit Frontend — Patent Prior-Art Search Strategy Generator.

Place this file at:
    analyzer/search_strategy_analyse/search_strategy_app.py

Run standalone:
    streamlit run search_strategy_app.py

Or call render_search_strategy_page() from the main app as a tab.
"""

import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_THIS_DIR    = Path(__file__).resolve().parent          # search_strategy_analyse/
_ANALYZER_DIR = _THIS_DIR.parent                        # analyzer/
_PROJECT_ROOT = _ANALYZER_DIR.parent                    # project root

sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_ANALYZER_DIR))
sys.path.insert(0, str(_THIS_DIR))

OUTPUT_DIR  = _ANALYZER_DIR / "document_text_output"
RESULT_DIR  = _THIS_DIR / "analyse_result"
REPORT_PATH = RESULT_DIR / "search_strategy_report.md"

OUTPUT_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

import streamlit as st

# ── Standalone page config ────────────────────────────────────────────────────
try:
    st.set_page_config(
        page_title="Patent Search Strategy",
        page_icon="🔍",
        layout="wide",
    )
except st.errors.StreamlitAPIException:
    pass  # Already configured by parent app


# ─────────────────────────────────────────────────────────────────────────────
# Helper — file status indicator
# ─────────────────────────────────────────────────────────────────────────────

def _file_status(path: Path, label: str, required: bool = False):
    """Render a success/warning/info indicator for an input file."""
    if path.exists() and path.stat().st_size > 0:
        size_kb = path.stat().st_size / 1024
        st.success(f"✅ {label} ({size_kb:.1f} KB)")
    elif required:
        st.warning(f"⚠️ {label} — not found")
    else:
        st.info(f"ℹ️ {label} — not found (optional)")


# ─────────────────────────────────────────────────────────────────────────────
# Main render function
# ─────────────────────────────────────────────────────────────────────────────

def render_search_strategy_page():
    """
    Render the Prior-Art Search Strategy page.
    Call from the main app or run standalone.
    """

    st.title("🔍 Prior-Art Search Strategy Generator")
    st.markdown(
        "Generates a structured 10-section prior-art search strategy report "
        "from extracted patent documents. "
        "Run the **Patent Document Analyser** tab first to extract text."
    )

    # ── Input file status ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📂 Input File Status")

    desc_path    = OUTPUT_DIR / "description.md"
    claims_path  = OUTPUT_DIR / "claims.md"
    drawing_path = OUTPUT_DIR / "drawing.md"

    col1, col2, col3 = st.columns(3)
    with col1:
        _file_status(desc_path,    "description.md",  required=False)
    with col2:
        _file_status(claims_path,  "claims.md",        required=False)
    with col3:
        _file_status(drawing_path, "drawing.md",       required=False)

    any_present = any(
        p.exists() and p.stat().st_size > 0
        for p in [desc_path, claims_path, drawing_path]
    )

    if not any_present:
        st.error(
            "❌ No input files found in document_text_output/. "
            "Please extract documents first."
        )
        return

    # ── Settings ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚙️ Settings")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        model_name = st.text_input(
            "Ollama model",
            value="gpt-oss:120b-cloud",
            help="Any Ollama-hosted model. Larger models give better results.",
        )
    with col_b:
        max_tokens = st.number_input(
            "Max tokens",
            min_value=2048,
            max_value=32768,
            value=8192,
            step=1024,
            help="Increase if the report is truncated.",
        )
    with col_c:
        inject_resources = st.checkbox(
            "Inject reference files into prompt",
            value=True,
            help=(
                "Appends ANSERA operators, IPC/CPC hints, and database "
                "priority reference to the system prompt. Disable for small "
                "context-window models."
            ),
        )

    # ── Generate button ───────────────────────────────────────────────────────
    st.markdown("---")
    run_col, _ = st.columns([1, 3])
    with run_col:
        run_button = st.button(
            "🚀 Generate Search Strategy",
            type="primary",
            use_container_width=True,
        )

    # ── Run analysis ──────────────────────────────────────────────────────────
    if run_button:
        with st.spinner("🔍 Analysing claims and generating prior-art search strategy..."):
            try:
                from search_core.ollama_client       import OllamaClient
                from search_config.settings          import SearchStrategySettings
                from search_strategy_analyzer        import SearchStrategyAnalyzer

                settings = SearchStrategySettings(
                    model_name=model_name,
                    max_tokens=int(max_tokens),
                    input_dir=OUTPUT_DIR,
                    inject_ansera_operators=inject_resources,
                    inject_ipc_hints=inject_resources,
                    inject_database_priority=inject_resources,
                )

                client   = OllamaClient(
                    model_name=model_name,
                    timeout=settings.timeout,
                )
                analyzer = SearchStrategyAnalyzer(
                    ollama_client=client,
                    settings=settings,
                )
                result = analyzer.analyze()

            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                return

        # ── Status banner ─────────────────────────────────────────────────────
        if result.status == "ERROR":
            st.error(f"❌ Generation failed.\n\n{result.error_message}")
            return

        if result.status == "PARTIAL":
            st.warning(
                "⚠️ Report was generated but may be incomplete. "
                "Review the full report below."
            )
        else:
            st.success("✅ Search strategy report generated successfully!")

        if result.error_message:
            st.warning(result.error_message)

        _render_results(result)

    # ── Show saved report if available and button not pressed ─────────────────
    elif REPORT_PATH.exists():
        st.markdown("---")
        st.info(
            "A previously generated report is available. "
            "Press **Generate Search Strategy** to regenerate."
        )
        saved = REPORT_PATH.read_text(encoding="utf-8")
        with st.expander("📄 View saved report", expanded=False):
            st.markdown(saved)
        st.download_button(
            label="⬇️ Download saved report",
            data=saved,
            file_name="search_strategy_report.md",
            mime="text/markdown",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Result rendering
# ─────────────────────────────────────────────────────────────────────────────

def _render_results(result):
    """Render all result panels after a successful analysis."""

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Report Summary")

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Keyword Marks",       result.num_marks)
    with m2:
        st.metric("Search Combinations", result.num_search_combinations)
    with m3:
        st.metric("CPC/IPC Codes",       len(result.classification_codes))
    with m4:
        st.metric("Description", "✅" if result.input_status.description_present else "—")
    with m5:
        st.metric("Drawing",     "✅" if result.input_status.drawing_present     else "—")

    # ── Technical conclusion ──────────────────────────────────────────────────
    if result.technical_conclusion:
        st.markdown("---")
        st.subheader("🎯 Technical Conclusion (Section 3)")
        st.info(result.technical_conclusion)

    # ── Boolean strings preview ───────────────────────────────────────────────
    if result.broad_boolean_string or result.narrow_boolean_string:
        st.markdown("---")
        st.subheader("🔤 Boolean Strings (Section 6)")
        col_broad, col_narrow = st.columns(2)
        with col_broad:
            st.markdown("**Broad string (high recall)**")
            st.code(result.broad_boolean_string or "— not extracted —", language="text")
        with col_narrow:
            st.markdown("**Narrow string (high precision)**")
            st.code(result.narrow_boolean_string or "— not extracted —", language="text")

    # ── Classification codes ──────────────────────────────────────────────────
    if result.classification_codes:
        st.markdown("---")
        st.subheader("🏷️ Classification Codes (Section 8)")
        st.markdown("  |  ".join(f"`{c}`" for c in result.classification_codes))

    # ── Full report ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Full Report")

    tab_rendered, tab_raw, tab_download = st.tabs([
        "📄 Rendered Report",
        "🔤 Raw Markdown",
        "💾 Download",
    ])

    with tab_rendered:
        st.markdown(result.full_report)

    with tab_raw:
        st.text_area(
            "Raw Markdown",
            value=result.full_report,
            height=600,
            label_visibility="collapsed",
        )

    with tab_download:
        st.markdown(f"**Saved to:** `{REPORT_PATH}`")
        st.download_button(
            label="⬇️ Download search_strategy_report.md",
            data=result.full_report,
            file_name="search_strategy_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.markdown("---")
        st.markdown("**Debug — raw metrics:**")
        st.json(result.to_dict())


# ── Standalone entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    render_search_strategy_page()
