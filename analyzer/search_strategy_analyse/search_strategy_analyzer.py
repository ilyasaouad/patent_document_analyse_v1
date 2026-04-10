"""
search_strategy_analyzer.py — main entry point for prior-art search
strategy generation.

Mirrors claims_legal_analyzer.py in structure and calling convention.

Usage
-----
    from search_core import OllamaClient
    from search_strategy_analyzer import SearchStrategyAnalyzer

    client   = OllamaClient(model_name="gpt-oss:120b-cloud")
    analyzer = SearchStrategyAnalyzer(ollama_client=client)
    result   = analyzer.analyze()

    print(result.full_report)
    print(result.num_marks)
"""

from pathlib import Path
from typing import Optional

from search_core.ollama_client  import OllamaClient
from search_core.search_models  import SearchStrategyResult, parse_full_result
from search_config.settings     import SearchStrategySettings
from search_config.search_prompts import build_system_prompt
from search_utils.file_loader   import DocumentLoader


class SearchStrategyAnalyzer:
    """
    Reads patent document text files and produces a prior-art search
    strategy report using an Ollama-hosted LLM.

    Parameters
    ----------
    ollama_client : OllamaClient
        A configured OllamaClient instance.
    settings : SearchStrategySettings, optional
        Override any default setting (model, paths, token limits).
        If not provided, defaults are used.
    input_dir : str or Path, optional
        Override the input directory from settings.
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        settings: Optional[SearchStrategySettings] = None,
        input_dir: Optional[str | Path] = None,
    ):
        self.client   = ollama_client
        self.settings = settings or SearchStrategySettings()

        # Allow caller to override input_dir without touching settings
        if input_dir is not None:
            self.settings.input_dir = Path(input_dir)

    # ── Public entry point ────────────────────────────────────────────────────

    def analyze(self) -> SearchStrategyResult:
        """
        Run the full search strategy analysis pipeline:

        1. Load input files from document_text_output/
        2. Build system prompt from search_prompts.py + resource files
        3. Build user message with file content
        4. Call the LLM
        5. Parse the report into SearchStrategyResult
        6. Save the report to analyse_result/

        Returns
        -------
        SearchStrategyResult
            Fully populated result object. Check result.status for
            SUCCESS / PARTIAL / ERROR.
        """

        # ── Step 1: Load documents ────────────────────────────────────────────
        loader = DocumentLoader(
            input_dir=self.settings.input_dir,
            description_filename=self.settings.description_filename,
            claims_filename=self.settings.claims_filename,
            drawing_filename=self.settings.drawing_filename,
        )
        docs = loader.load()

        if not docs.any_present():
            result = SearchStrategyResult()
            result.status = "ERROR"
            result.error_message = (
                "No input files found in: "
                f"{self.settings.input_dir}\n"
                "Please run the Patent Document Analyser to extract text first."
            )
            return result

        # ── Step 2: Build prompts ─────────────────────────────────────────────
        system_prompt = build_system_prompt(self.settings)
        user_message  = loader.build_user_message(docs)

        # ── Step 3: Call the LLM ──────────────────────────────────────────────
        try:
            raw_response = self.client.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
            )
        except RuntimeError as e:
            result = SearchStrategyResult()
            result.input_status = docs.input_status
            result.status = "ERROR"
            result.error_message = str(e)
            return result

        if not raw_response or not raw_response.strip():
            result = SearchStrategyResult()
            result.input_status = docs.input_status
            result.status = "ERROR"
            result.error_message = "LLM returned an empty response."
            return result

        # ── Step 4: Parse result ──────────────────────────────────────────────
        result = parse_full_result(
            report=raw_response,
            input_status=docs.input_status,
        )

        # ── Step 5: Save report ───────────────────────────────────────────────
        try:
            output_path = self.settings.output_path()
            output_path.write_text(raw_response, encoding="utf-8")
        except Exception as e:
            # Non-fatal — report is still returned to the caller
            result.error_message = (
                f"Report generated successfully but could not be saved: {e}"
            )

        return result
