"""
search_config — settings and prompt builder for search strategy analysis.
"""

from .settings import SearchStrategySettings
from .search_prompts import build_system_prompt

__all__ = [
    "SearchStrategySettings",
    "build_system_prompt",
]
