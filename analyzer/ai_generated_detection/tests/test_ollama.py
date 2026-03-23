from unittest.mock import patch, MagicMock
from core.ollama_client import OllamaClient

@patch("requests.get")
def test_test_connection(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": [{"name": "gpt-oss:120b-cloud"}]}
    mock_get.return_value = mock_response

    client = OllamaClient("gpt-oss:120b-cloud")
    assert client.test_connection() == True

@patch("requests.post")
def test_generate(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "test response"}
    mock_post.return_value = mock_response

    client = OllamaClient("model")
    res = client.generate("prompt")
    assert res == "test response"
