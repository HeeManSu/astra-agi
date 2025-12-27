
import unittest
import json
import io
from unittest.mock import MagicMock, patch
from observability.instrumentation.models.llm import LLMRequest, LLMResponse
from observability.instrumentation.providers.bedrock.adapter import BedrockAdapter
from observability.instrumentation.core.operations import OperationSpec

class TestBedrockAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = BedrockAdapter()
        self.op = OperationSpec(
            name="InvokeModel",
            method_name="invoke_model",
            span_name="bedrock.invoke_model",
            kind="generate"
        )

    def test_parse_anthropic_request(self):
        """Test parsing a Claude request body."""
        body = {
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100
        }
        kwargs = {
            "body": json.dumps(body),
            "modelId": "anthropic.claude-3-sonnet"
        }
        
        request = self.adapter.parse_request(self.op, (), kwargs, truncate_limit=1000)
        
        self.assertIsInstance(request, LLMRequest)
        self.assertEqual(request.messages[0].content, "Hello")

    def test_parse_anthropic_response(self):
        """Test parsing a Claude response body."""
        response_body = {
            "content": [{"type": "text", "text": "Hi there"}],
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }
        
        # Simulate botocore response structure
        response = {
            "body": io.BytesIO(json.dumps(response_body).encode("utf-8")),
            "_astra_response_body": response_body
        }
        
        llm_response = self.adapter.parse_response(self.op, response, truncate_limit=1000)
        
        self.assertIsInstance(llm_response, LLMResponse)
        self.assertEqual(llm_response.content, "Hi there")
        self.assertIsNotNone(llm_response.usage)
        if llm_response.usage:
            self.assertEqual(llm_response.usage.prompt_tokens, 10)

if __name__ == "__main__":
    unittest.main()
