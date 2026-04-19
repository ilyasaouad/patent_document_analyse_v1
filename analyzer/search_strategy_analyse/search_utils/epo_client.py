"""
epo_client.py — fetches CPC/IPC classification hierarchy from the EPO
Linked Open Data API.

No authentication required. Returns structured classification trees
that can be injected into the LLM prompt for precise subgroup selection.

API base: https://data.epo.org/linked-data/def/cpc/{SYMBOL}.json

Improvements over v1:
  - Parallel child fetching via ThreadPoolExecutor
  - Optional disk cache (shelve) to avoid re-fetching stable CPC data
  - Retry logic with exponential back-off
  - Correct tree rendering (└── for last child, ├── for others)
  - Typed raw API response via TypedDict
  - _extract_title() helper — no more scattered isinstance checks
"""

import json
import logging
import shelve
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)


# ── API response shape ────────────────────────────────────────────────────────

class _NarrowerItem(TypedDict, total=False):
    label: str
    title: str | list[str]


class _PrimaryTopic(TypedDict, total=False):
    fullTitle: str | list[str]
    title: str | list[str]
    level: int
    narrower: list[_NarrowerItem] | _NarrowerItem


class _ApiResult(TypedDict, total=False):
    primaryTopic: _PrimaryTopic


class _ApiResponse(TypedDict, total=False):
    result: _ApiResult


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class CPCNode:
    """A single node in the CPC hierarchy tree."""
    symbol: str
    title: str
    level: int = 0
    children: list["CPCNode"] = field(default_factory=list)

    def to_tree_string(self, _indent: int = 0, _last: bool = True) -> str:
        """Render this node and its children as an indented tree string."""
        if _indent == 0:
            prefix = ""
            connector = ""
        else:
            prefix = "│   " * (_indent - 1)
            connector = "└── " if _last else "├── "

        line = f"{prefix}{connector}{self.symbol}  —  {self.title}"
        lines = [line]

        for i, child in enumerate(self.children):
            is_last = (i == len(self.children) - 1)
            lines.append(child.to_tree_string(_indent + 1, _last=is_last))

        return "\n".join(lines)


# ── Client ────────────────────────────────────────────────────────────────────

class EPOClassificationClient:
    """
    Fetches CPC classification hierarchy from EPO Linked Open Data.

    Parameters
    ----------
    base_url : str
        Base URL for the EPO linked data API.
    timeout : int
        HTTP request timeout in seconds.
    max_depth : int
        Maximum depth to recurse when fetching hierarchy.
        0 = just the requested symbol, 1 = its direct children, etc.
    max_workers : int
        Thread pool size for parallel child fetching.
    retries : int
        Number of retry attempts on transient HTTP errors.
    retry_delay : float
        Base delay in seconds between retries (doubles each attempt).
    cache_path : str or None
        Path prefix for a shelve disk cache. Pass None to disable.
        Example: "/tmp/epo_cache" → creates /tmp/epo_cache.db (or similar).
    """

    def __init__(
        self,
        base_url: str = "https://data.epo.org/linked-data/def/cpc",
        timeout: int = 15,
        max_depth: int = 2,
        max_workers: int = 8,
        retries: int = 3,
        retry_delay: float = 0.5,
        cache_path: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_workers = max_workers
        self.retries = retries
        self.retry_delay = retry_delay
        self.cache_path = cache_path

        # In-memory cache (session-scoped)
        self._mem_cache: dict[str, _ApiResponse] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_hierarchy(self, class_symbol: str) -> Optional[CPCNode]:
        """
        Fetch the full CPC hierarchy for a class symbol.

        Parameters
        ----------
        class_symbol : str
            A CPC class symbol, e.g. "G06", "H03", "A61".

        Returns
        -------
        CPCNode or None
            Root node with children populated up to max_depth,
            or None if the API call failed.
        """
        logger.info("Fetching CPC hierarchy for: %s", class_symbol)
        return self._fetch_node(class_symbol, depth=0)

    def fetch_multiple(self, class_symbols: list[str]) -> list[CPCNode]:
        """
        Fetch hierarchies for multiple class symbols **in parallel**.

        Returns only the nodes that were successfully fetched,
        preserving input order.
        """
        symbols = [s.strip() for s in class_symbols]
        results: dict[str, Optional[CPCNode]] = {}

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(symbols) or 1)) as pool:
            futures = {pool.submit(self.fetch_hierarchy, sym): sym for sym in symbols}
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    results[sym] = future.result()
                except Exception as exc:
                    logger.warning("fetch_hierarchy(%s) raised: %s", sym, exc)
                    results[sym] = None

        return [results[sym] for sym in symbols if results.get(sym) is not None]  # type: ignore[misc]

    def build_enriched_hints(self, class_symbols: list[str]) -> str:
        """
        Fetch hierarchies for the given classes and format them as a
        text block suitable for injection into the LLM system prompt.

        Parameters
        ----------
        class_symbols : list[str]
            CPC class symbols identified by Phase 1, e.g. ["G06", "H03"].

        Returns
        -------
        str
            Formatted text block with full CPC trees, or a fallback
            message if no data could be fetched.
        """
        nodes = self.fetch_multiple(class_symbols)

        if not nodes:
            logger.warning("Could not fetch any CPC hierarchy data from EPO API.")
            return (
                "EPO API was unreachable. Use your built-in knowledge of CPC/IPC\n"
                "classification to select the most specific subgroups available."
            )

        parts = [
            "LIVE CPC CLASSIFICATION HIERARCHY (from EPO Linked Open Data)",
            "=" * 65,
            "",
            "The following CPC hierarchy trees were fetched live from the EPO",
            "API for the classes identified as most relevant to this patent.",
            "Select the most specific subgroup(s) from these trees for Section 8.",
            "",
        ]

        for node in nodes:
            parts.append("─" * 65)
            parts.append(node.to_tree_string())
            parts.append("")

        parts.append("─" * 65)
        parts.append(
            "NOTE: These are the verified, up-to-date CPC codes. Prefer these\n"
            "over your training data. Select codes at the most specific level\n"
            "that matches the patent's technical features."
        )

        return "\n".join(parts)

    # ── Internal methods ──────────────────────────────────────────────────────

    def _fetch_node(self, symbol: str, depth: int) -> Optional[CPCNode]:
        """Recursively fetch a CPC node and its children (parallel at each level)."""
        data = self._api_call(symbol)
        if data is None:
            return None

        topic: _PrimaryTopic = data.get("result", {}).get("primaryTopic", {})
        title = _extract_title(topic.get("fullTitle") or topic.get("title"))
        level: int = topic.get("level", 0)

        node = CPCNode(symbol=symbol, title=title, level=level)

        if depth >= self.max_depth:
            return node

        # Normalise narrower to a list
        narrower_raw = topic.get("narrower", [])
        if isinstance(narrower_raw, dict):
            narrower_raw = [narrower_raw]

        child_labels = [
            item["label"]
            for item in narrower_raw
            if item.get("label")
        ]

        if not child_labels:
            return node

        # Fetch children in parallel
        child_results: dict[str, Optional[CPCNode]] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(child_labels))) as pool:
            futures = {
                pool.submit(self._fetch_node, label, depth + 1): label
                for label in child_labels
            }
            for future in as_completed(futures):
                label = futures[future]
                try:
                    child_results[label] = future.result()
                except Exception as exc:
                    logger.warning("Child fetch(%s) raised: %s", label, exc)
                    child_results[label] = None

        # Preserve original order; fall back to stub node on failure
        for item in narrower_raw:
            label = item.get("label", "")
            if not label:
                continue
            child = child_results.get(label)
            if child is not None:
                node.children.append(child)
            else:
                # Fallback stub so the symbol is still visible in the tree
                fallback_title = _extract_title(item.get("title"))
                node.children.append(CPCNode(symbol=label, title=fallback_title))

        return node

    def _api_call(self, symbol: str) -> Optional[_ApiResponse]:
        """
        Fetch a single CPC symbol from the EPO API with retry logic.

        Checks memory cache, then disk cache (if configured), then
        makes an HTTP request. Retries up to `self.retries` times on
        transient errors using exponential back-off.
        """
        url_symbol = symbol.replace(" ", "").replace("/", "-")

        # 1. Memory cache
        if url_symbol in self._mem_cache:
            return self._mem_cache[url_symbol]

        # 2. Disk cache
        if self.cache_path:
            try:
                with shelve.open(self.cache_path) as db:
                    if url_symbol in db:
                        data = db[url_symbol]
                        self._mem_cache[url_symbol] = data
                        return data
            except Exception as exc:
                logger.warning("Disk cache read failed for %s: %s", symbol, exc)

        # 3. HTTP request with retries
        url = f"{self.base_url}/{url_symbol}.json"
        last_error: Optional[Exception] = None

        for attempt in range(self.retries + 1):
            if attempt > 0:
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.debug("Retry %d/%d for %s (waiting %.1fs)", attempt, self.retries, symbol, delay)
                time.sleep(delay)

            try:
                request = urllib.request.Request(
                    url,
                    headers={"Accept": "application/json"},
                    method="GET",
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8")
                    data: _ApiResponse = json.loads(raw)

                    self._mem_cache[url_symbol] = data

                    if self.cache_path:
                        try:
                            with shelve.open(self.cache_path) as db:
                                db[url_symbol] = data
                        except Exception as exc:
                            logger.warning("Disk cache write failed for %s: %s", symbol, exc)

                    return data

            except urllib.error.HTTPError as e:
                # Don't retry on client errors (4xx)
                if 400 <= e.code < 500:
                    logger.warning("EPO API HTTP %d for %s — not retrying", e.code, symbol)
                    return None
                last_error = e
                logger.warning("EPO API HTTP %d for %s (attempt %d)", e.code, symbol, attempt + 1)

            except urllib.error.URLError as e:
                last_error = e
                logger.warning("EPO API URLError for %s (attempt %d): %s", symbol, attempt + 1, e)

            except json.JSONDecodeError as e:
                logger.warning("EPO API returned invalid JSON for %s: %s", symbol, e)
                return None  # JSON errors are not transient — don't retry

        logger.error("EPO API failed for %s after %d attempts: %s", symbol, self.retries + 1, last_error)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_title(raw: str | list[str] | None) -> str:
    """
    Normalise a title field that may be a string, a list of strings,
    or absent. Returns the first non-empty string, or "".
    """
    if not raw:
        return ""
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return ""
    return raw.strip()