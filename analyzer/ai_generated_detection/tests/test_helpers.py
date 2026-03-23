from utils.helpers import (
    truncate_text, parse_json_safe, normalize_score,
    extract_figure_references, extract_element_references,
    format_percentage, safe_divide
)

def test_truncate_text():
    text = "First sentence. Second sentence. Third sentence."
    assert truncate_text(text, 25) == "First sentence."
    assert truncate_text(text, 100) == text

def test_parse_json_safe():
    assert parse_json_safe('{"key": "value"}', {}) == {"key": "value"}
    assert parse_json_safe('Prefix ```json\n{"score": 0.5}\n``` Suffix', {}) == {"score": 0.5}
    assert parse_json_safe('Text {"nested": {"a": 1}} text', {}) == {"nested": {"a": 1}}
    assert parse_json_safe('Bad JSON', {"default": True}) == {"default": True}

def test_normalize_score():
    assert normalize_score(0.5) == 0.5
    assert normalize_score(75) == 0.75
    assert normalize_score("0.9") == 0.9
    assert normalize_score("bad", 0.5) == 0.5

def test_extract_figure_references():
    text = "As shown in FIG. 1, Figure 2, and fig 3A."
    assert extract_figure_references(text) == ["1", "2", "3A"]

def test_extract_element_references():
    text = "element 10 connects to reference numeral 20 and numeral 10."
    refs = extract_element_references(text)
    assert refs == ["10", "20"]

def test_format_percentage():
    assert format_percentage(0.753, 1) == "75.3%"

def test_safe_divide():
    assert safe_divide(10, 2) == 5.0
    assert safe_divide(10, 0, default=0.0) == 0.0
