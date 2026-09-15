import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from llm_provider import query_llm


class TestLLMProviderAbstraction(unittest.TestCase):

    @patch("llm_provider._query_ollama")
    def test_default_ollama_provider(self, mock_ollama):
        mock_ollama.return_value = "Ollama test response"
        messages = [{"role": "user", "content": "Hello"}]
        
        result = query_llm(messages, provider="ollama")
        self.assertEqual(result, "Ollama test response")
        mock_ollama.assert_called_once()

    @patch("llm_provider._query_ollama")
    def test_openai_fallback_without_key(self, mock_ollama):
        """When OPENAI_API_KEY is empty/placeholder, fallback to Ollama cleanly."""
        mock_ollama.return_value = "Ollama fallback response"
        messages = [{"role": "user", "content": "Retention advice?"}]

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            result = query_llm(messages, provider="openai")
            self.assertEqual(result, "Ollama fallback response")
            mock_ollama.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_openai_api_call_with_key(self, mock_urlopen):
        """When valid OPENAI_API_KEY is present, query OpenAI endpoint."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "OpenAI GPT response"}}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        messages = [{"role": "user", "content": "How to improve retention?"}]
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key-12345"}):
            result = query_llm(messages, provider="openai")
            self.assertEqual(result, "OpenAI GPT response")

    @patch("llm_provider._query_ollama")
    def test_anthropic_fallback_without_key(self, mock_ollama):
        """When ANTHROPIC_API_KEY is empty/placeholder, fallback to Ollama cleanly."""
        mock_ollama.return_value = "Ollama Claude fallback response"
        messages = [{"role": "user", "content": "Retention strategy"}]

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            result = query_llm(messages, provider="claude")
            self.assertEqual(result, "Ollama Claude fallback response")
            mock_ollama.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_anthropic_api_call_with_key(self, mock_urlopen):
        """When valid ANTHROPIC_API_KEY is present, query Anthropic endpoint."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"content": [{"text": "Anthropic Claude response"}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        messages = [{"role": "system", "content": "You are helpful"}, {"role": "user", "content": "Tell me about churn"}]
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test-key-12345"}):
            result = query_llm(messages, provider="anthropic")
            self.assertEqual(result, "Anthropic Claude response")


if __name__ == "__main__":
    unittest.main()
