# Skill: Patent Prior-Art Search Strategy Generator

## Purpose

This skill reads extracted patent documents (description, claims, drawings)
and produces a complete, structured prior-art search strategy report
suitable for a patent examiner.

## When to trigger this skill

Trigger this skill when the user wants to:
- Generate a prior-art search strategy for a set of patent claims
- Produce keyword marks (A, B, C …) for use in EPO ANSERA or Espacenet
- Build Boolean search strings for patent database searching
- Get IPC / CPC classification code suggestions for a patent application
- Produce a prior-art search report to hand to a patent examiner

## Input

The skill reads from:
```
analyzer/document_text_output/
├── description.md    (patent description — optional)
├── claims.md         (patent claims — optional)
└── drawing.md        (drawing reference text — optional)
```

At least one file must be present. The skill notes any absent files in
the output report and proceeds with available content.

## Output

A Markdown report saved to:
```
analyzer/search_strategy_analyse/analyse_result/search_strategy_report.md
```

The report contains 10 sections:
1. Input Status
2. Claim Analysis (independent + dependent claims explained)
3. Technical Conclusion
4. Prior-Art Keyword Structure (Marks A, B, C … with ANSERA operators)
5. Recommended Search Combinations
6. Example Boolean Strings (broad + narrow)
7. Prior-Art Search Table
8. Classification Codes (IPC / CPC)
9. Recommended Databases and Search Order
10. Examiner Notes

## Entry point

```python
from search_core import OllamaClient
from search_strategy_analyzer import SearchStrategyAnalyzer

client   = OllamaClient(model_name="gpt-oss:120b-cloud")
analyzer = SearchStrategyAnalyzer(ollama_client=client)
result   = analyzer.analyze()
```

## Key files

| File | Role |
|------|------|
| `search_strategy_analyzer.py` | Main entry point — `.analyze()` method |
| `search_config/search_prompts.py` | System prompt builder |
| `search_config/settings.py` | Model, paths, token limits |
| `search_core/search_models.py` | Result dataclass + parsers |
| `search_core/ollama_client.py` | LLM HTTP client |
| `search_utils/file_loader.py` | Reads input .md files, builds user message |
| `search_utils/helpers.py` | Section extraction, mark counting |
| `resources/guidelines/ansera_operators.txt` | ANSERA operator reference |
| `resources/guidelines/ipc_cpc_hints.txt` | IPC/CPC code hints |
| `resources/guidelines/database_priority.txt` | Database search order |

## Dependencies

- Python 3.10+
- No external libraries required (uses only stdlib: pathlib, re, json,
  urllib, dataclasses)
- Requires a running Ollama instance with the configured model loaded
