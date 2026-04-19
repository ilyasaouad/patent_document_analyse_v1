"""
search_strategy_analyzer.py — main entry point for prior-art search
strategy generation.

Supports two modes:
  - Hybrid (default): Phase 1 identifies CPC classes → EPO API fetches
    live hierarchy → Phase 2 writes the full report with verified codes.
  - Static fallback: Single LLM call using the static ipc_cpc_hints.txt
    file (used when enable_epo_enrichment=False or API is unreachable).

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

from loguru import logger

from search_core.ollama_client  import OllamaClient
from search_core.search_models  import SearchStrategyResult, parse_full_result
from search_config.settings     import SearchStrategySettings
from search_config.search_prompts import (
    build_system_prompt,
    build_enriched_system_prompt,
    build_phase1_prompt,
    parse_phase1_classes,
)
from search_utils.file_loader   import DocumentLoader
from search_utils.epo_client    import EPOClassificationClient


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
        Run the full search strategy analysis pipeline.

        If EPO enrichment is enabled (default), runs a two-phase pipeline:
          Phase 1: Quick LLM call to identify relevant CPC classes
          API:     Fetch live CPC hierarchy from EPO Linked Data
          Phase 2: Full report with enriched CPC data in the prompt

        If EPO enrichment is disabled or fails, falls back to a single
        LLM call using the static ipc_cpc_hints.txt file.

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

        user_message = loader.build_user_message(docs)

        # ── Step 2: Build system prompt (hybrid or static) ────────────────────
        enriched_mode = False
        if self.settings.enable_epo_enrichment:
            system_prompt = self._build_enriched_prompt(user_message)
            enriched_mode = True
        else:
            system_prompt = build_system_prompt(self.settings)

        # When in enriched mode, append a hard instruction to the user message
        # so the LLM cannot ignore it (user-turn instructions take priority)
        final_user_message = user_message
        if enriched_mode:
            final_user_message = (
                user_message
                + "\n\n"
                + "=" * 65
                + "\n"
                + "CRITICAL INSTRUCTION — READ BEFORE GENERATING\n"
                + "=" * 65
                + "\n"
                + "For the classification section you MUST output TWO separate tables:\n"
                + "1. ## SECTION 8A — CLASSIFICATION CODES (USING LIVE EPO API)\n"
                + "   Use ONLY the exact CPC subgroups provided in the LIVE CPC CLASSIFICATION HIERARCHY\n"
                + "   block in the system prompt. Do not invent codes.\n"
                + "2. ## SECTION 8B — CLASSIFICATION CODES (LLM INTERNAL BASELINE)\n"
                + "   Use your own internal knowledge to suggest CPC codes\n"
                + "   INDEPENDENTLY of the API data above.\n"
                + "Both tables must use the column format:\n"
                + "| Code | Title | Relevant Technical Terms | Relevance % | Why relevant |\n"
                + "DO NOT output a single '## SECTION 8'. You MUST output 8A and 8B.\n"
                + "=" * 65
            )

        # ── Step 3: Call the LLM (Phase 2 — full report) ──────────────────────
        try:
            logger.info("Phase 2: Generating full search strategy report...")
            raw_response = self.client.chat(
                system_prompt=system_prompt,
                user_message=final_user_message,
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

    # ── Private: hybrid enrichment pipeline ───────────────────────────────────

    def _build_enriched_prompt(self, user_message: str) -> str:
        """
        Run Phase 1 (class identification) + EPO API enrichment.

        Falls back to static prompt if Phase 1 or API fails.

        Parameters
        ----------
        user_message : str
            The assembled user message with patent document content.

        Returns
        -------
        str
            The enriched system prompt (or static fallback).
        """
        # ── Phase 1: Identify relevant CPC classes ────────────────────────────
        logger.info("Phase 1: Identifying relevant CPC classes...")
        phase1_prompt = build_phase1_prompt(self.settings)

        try:
            phase1_response = self.client.chat(
                system_prompt=phase1_prompt,
                user_message=user_message,
                temperature=0.1,
                max_tokens=self.settings.phase1_max_tokens,
            )
        except RuntimeError as e:
            logger.warning(f"Phase 1 LLM call failed: {e}. Falling back to static hints.")
            return build_system_prompt(self.settings)

        if not phase1_response or not phase1_response.strip():
            logger.warning("Phase 1 returned empty response. Falling back to static hints.")
            return build_system_prompt(self.settings)

        # ── Parse class codes from Phase 1 response ───────────────────────────
        class_codes = parse_phase1_classes(phase1_response)
        logger.info(f"Phase 1 identified classes: {class_codes}")

        if not class_codes:
            logger.warning("Phase 1 returned no valid class codes. Falling back to static hints.")
            return build_system_prompt(self.settings)

        # ── EPO API: Fetch live CPC hierarchy ─────────────────────────────────
        logger.info(f"Fetching CPC hierarchy from EPO API for: {class_codes}")
        epo_client = EPOClassificationClient(
            base_url=self.settings.epo_api_base_url,
            timeout=self.settings.epo_api_timeout,
            max_depth=self.settings.epo_api_depth,
            max_workers=self.settings.epo_api_workers,
            retries=self.settings.epo_api_retries,
            cache_path=self.settings.epo_api_cache,
        )

        enriched_text = epo_client.build_enriched_hints(class_codes)

        # ── Build enriched Phase 2 prompt ─────────────────────────────────────
        logger.info("Building enriched system prompt with live CPC data.")
        return build_enriched_system_prompt(self.settings, enriched_text)
