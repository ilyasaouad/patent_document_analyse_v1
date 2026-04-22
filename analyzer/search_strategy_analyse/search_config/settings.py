"""
settings.py — configuration for SearchStrategyAnalyzer.

All paths, model defaults, and token limits are defined here.
Change values here without touching any other file.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ── Directory layout (relative to this file) ─────────────────────────────────

_THIS_DIR      = Path(__file__).resolve().parent          # search_config/
_MODULE_DIR    = _THIS_DIR.parent                         # search_strategy_analyse/
_RESOURCES_DIR = _MODULE_DIR / "resources" / "guidelines"
_RESULTS_DIR   = _MODULE_DIR / "analyse_result"


@dataclass
class SearchStrategySettings:
    """
    Central configuration object for SearchStrategyAnalyzer.

    Instantiate with defaults or override any field:

        settings = SearchStrategySettings(model_name="llama3:70b")
    """

    # ── LLM settings ──────────────────────────────────────────────────────────
    model_name:  str   = "gpt-oss:120b-cloud"
    base_url:    str   = "http://localhost:11434"
    temperature: float = 0.1      # Low for deterministic patent analysis
    max_tokens:  int   = 8192     # Large context needed for full 10-section report
    timeout:     int   = 300      # Seconds — large models can be slow

    # ── Input directory ───────────────────────────────────────────────────────
    # Path to folder containing description.md, claims.md, drawing.md
    input_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
        / "document_text_output"
    )

    # ── Output ────────────────────────────────────────────────────────────────
    output_dir:      Path = field(default_factory=lambda: _RESULTS_DIR)
    output_filename: str  = "search_strategy_report.md"

    # ── Resource files (loaded into system prompt at runtime) ─────────────────
    ansera_operators_path: Path = field(
        default_factory=lambda: _RESOURCES_DIR / "ansera_operators.txt"
    )
    ipc_cpc_hints_path: Path = field(
        default_factory=lambda: _RESOURCES_DIR / "ipc_cpc_hints.txt"
    )
    database_priority_path: Path = field(
        default_factory=lambda: _RESOURCES_DIR / "database_priority.txt"
    )

    # ── EPO Linked Data API (for hybrid CPC enrichment) ────────────────────
    epo_api_base_url: str = "https://data.epo.org/linked-data/def/cpc"
    epo_api_timeout:  int = 15      # Seconds per API call
    epo_api_depth:    int = 4       # Recursion depth: 0=symbol only, 1=main group, 2...4=subgroups
    epo_api_workers:  int = 8       # Thread pool size for parallel requests
    epo_api_retries:  int = 3       # Max retry attempts for transient errors
    epo_api_cache:    Optional[str] = field(
        default_factory=lambda: str(_THIS_DIR / ".epo_cache.db")
    )
    enable_epo_enrichment: bool = True   # Set False to skip Phase 1 / API and use static hints only
    phase1_max_tokens: int = 256    # Phase 1 is a short response (just class codes)

    # ── Prompt behaviour ──────────────────────────────────────────────────────
    # Set to False to omit resource file content from the system prompt
    # (useful when using a very small context-window model)
    inject_ansera_operators: bool = True
    inject_ipc_hints:        bool = True
    inject_database_priority: bool = True

    # ── Input filenames ───────────────────────────────────────────────────────
    description_filename: str = "description.md"
    claims_filename:      str = "claims.md"
    drawing_filename:     str = "drawing.md"

    def output_path(self) -> Path:
        """Full path to the output report file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / self.output_filename

    def _read_resource(self, path: Path) -> str:
        """Read a resource file. Returns empty string if file does not exist."""
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def ansera_operators_text(self) -> str:
        return self._read_resource(self.ansera_operators_path) if self.inject_ansera_operators else ""

    def ipc_hints_text(self) -> str:
        return self._read_resource(self.ipc_cpc_hints_path) if self.inject_ipc_hints else ""

    def database_priority_text(self) -> str:
        return self._read_resource(self.database_priority_path) if self.inject_database_priority else ""
