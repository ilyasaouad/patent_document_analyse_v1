from config.prompts import PromptTemplates

def test_format_prompt():
    template = "Hello {name}, your score is {score}"
    result = PromptTemplates.format_prompt(template, name="Alice", score=100)
    assert result == "Hello Alice, your score is 100"

def test_prompts_exist():
    assert hasattr(PromptTemplates, "FINGERPRINT_SYSTEM")
