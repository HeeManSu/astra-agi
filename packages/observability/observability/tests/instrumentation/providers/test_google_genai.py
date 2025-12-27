
import unittest
from unittest.mock import MagicMock
from observability.instrumentation.models.llm import LLMRequest, LLMResponse
from observability.instrumentation.providers.google_genai.adapter import GoogleGenAIAdapter
from observability.instrumentation.core.operations import OperationSpec

class TestGoogleGenAIAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = GoogleGenAIAdapter()
        self.op = OperationSpec(
            name="generate_content",
            method_name="generate_content",
            span_name="google_genai.generate_content",
            kind="generate"
        )

    def test_parse_request_string(self):
        """Test parsing a simple string prompt."""
        # Adapter expects (self, model, contents) or similar based on its logic
        args = (MagicMock(), "gemini-pro", "Hello Gemini") 
        kwargs = {}
        
        request = self.adapter.parse_request(self.op, args, kwargs, truncate_limit=1000)
        
        self.assertIsInstance(request, LLMRequest)
        self.assertEqual(request.messages[0].content, "Hello Gemini")

    def test_parse_response_object(self):
        """Test parsing a GenerateContentResponse object."""
        mock_response = MagicMock()
        mock_response.text = "I am Gemini"
        mock_response.model = "gemini-pro"
        mock_response.role = "assistant"
        mock_response.finish_reason = "stop"
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 15
        
        llm_response = self.adapter.parse_response(self.op, mock_response, truncate_limit=1000)
        
        self.assertIsInstance(llm_response, LLMResponse)
        self.assertEqual(llm_response.content, "I am Gemini")
        self.assertIsNotNone(llm_response.usage)
        if llm_response.usage:
            self.assertEqual(llm_response.usage.prompt_tokens, 20)
            self.assertEqual(llm_response.usage.completion_tokens, 15)

if __name__ == "__main__":
    unittest.main()
