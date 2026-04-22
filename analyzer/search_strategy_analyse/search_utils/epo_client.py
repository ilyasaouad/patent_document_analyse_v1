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
    score: float = 0.0  # Relevance score (0.0 to 1.0+)

    def to_tree_string(self, _indent: int = 0, _last: bool = True, show_score: bool = False) -> str:
        """Render this node and its children as an indented tree string."""
        if _indent == 0:
            prefix = ""
            connector = ""
        else:
            prefix = "│   " * (_indent - 1)
            connector = "└── " if _last else "├── "

        score_tag = f" [{self.score:.2f}]" if show_score else ""
        line = f"{prefix}{connector}{self.symbol}{score_tag}  —  {self.title}"
        lines = [line]

        for i, child in enumerate(self.children):
            is_last = (i == len(self.children) - 1)
            lines.append(child.to_tree_string(_indent + 1, _last=is_last, show_score=show_score))

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
        Fetch hierarchies, rank them if possible, and format them as a
        text block suitable for injection into the LLM system prompt.
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
            "The following CPC hierarchy trees were fetched live for the",
            "classes most relevant to this patent.",
            "",
        ]

        for node in nodes:
            parts.append("─" * 65)
            # Show score if it's been calculated
            parts.append(node.to_tree_string(show_score=(node.score > 0)))
            parts.append("")

        parts.append("─" * 65)
        return "\n".join(parts)

    def score_and_rank(
        self,
        nodes: list[CPCNode],
        phase1_data: dict,
        ollama_client,
        embed_model: str = "nomic-embed-text"
    ) -> list[CPCNode]:
        """
        FULL SCORE ENGINE (STEP 2, 4 & 5)
        """
        raw_terms = phase1_data.get("terms", [])
        sections = phase1_data.get("cpc_sections", [])
        
        if not nodes or not raw_terms:
            return []

        # ── STEP 2: Rank terms & select Top-K ─────────────────────────
        # Criteria: importance (LLM) + specificity (word count)
        scored_terms = []
        for t in raw_terms:
            term_str = t.get("term", "")
            if not term_str: continue
            importance = float(t.get("importance", 3))
            # specificity bonus: longer phrases are usually better than single words
            specificity = len(term_str.split()) * 0.5
            scored_terms.append({
                "term": term_str,
                "score": importance + specificity
            })
        
        scored_terms.sort(key=lambda x: x["score"], reverse=True)
        top_k = scored_terms[:8] # Select top 8 terms for scoring
        
        # 1. Pre-calculate embeddings for top-k terms
        term_vecs = []
        for t in top_k:
            try:
                vec = ollama_client.embeddings(t["term"], model=embed_model)
                term_vecs.append({"term": t["term"], "vector": vec})
            except Exception as e:
                logger.warning(f"Embedding failed: {e}")

        # ── STEP 4: Tree Node Scoring ─────────────────────────────────
        # Formula: 0.5 * Similarity + 0.3 * Overlap + 0.2 * SectionBonus
        def score_recursive(node: CPCNode):
            if not node.title:
                node.score = 0.0
            else:
                # A. Embedding Similarity (0.5)
                sim_score = 0.0
                if term_vecs:
                    try:
                        node_vec = ollama_client.embeddings(node.title, model=embed_model)
                        # We use the average similarity to the cluster of top terms
                        similarities = [cosine_similarity(node_vec, tv["vector"]) for tv in term_vecs]
                        sim_score = max(similarities) if similarities else 0.0
                    except Exception: sim_score = 0.0

                # B. Term Overlap (0.3)
                overlap_count = 0
                node_lower = node.title.lower()
                for tv in term_vecs:
                    if tv["term"].lower() in node_lower:
                        overlap_count += 1
                overlap_score = min(1.0, overlap_count / 3.0) # Cap at 1.0 (3+ terms)

                # C. Section Bonus (0.2)
                section_bonus = 1.0 if node.symbol and node.symbol[0] in sections else 0.0

                # COMPOSITE SCORE
                node.score = (0.5 * sim_score) + (0.3 * overlap_score) + (0.2 * section_bonus)

            for child in node.children:
                score_recursive(child)

        for root in nodes:
            score_recursive(root)

        # ── STEP 5: Final Selection ───────────────────────────────────
        all_nodes = []
        def flatten(node):
            all_nodes.append(node)
            for c in node.children: flatten(c)
        for root in nodes: flatten(root)

        all_nodes.sort(key=lambda n: n.score, reverse=True)

        final_selection = []
        seen_parents = set()
        for n in all_nodes:
            if len(final_selection) >= 5: break
            if n.score < 0.25: continue
            
            # Diversity: skip if same branch prefix
            prefix = n.symbol.split("/")[0] if "/" in n.symbol else n.symbol[:6]
            if prefix in seen_parents and len(final_selection) > 1:
                continue
            
            final_selection.append(n)
            seen_parents.add(prefix)

        return final_selection

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

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Manual cosine similarity calculation."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = sum(a * a for a in v1) ** 0.5
    magnitude2 = sum(b * b for b in v2) ** 0.5
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


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