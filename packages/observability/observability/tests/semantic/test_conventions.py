
import unittest

from observability.semantic.conventions import GenAIAttributes, LLMAttributes


class TestConventionChanges(unittest.TestCase):
    def test_backward_compatibility(self):
        """Test that GenAIAttributes still exists and maps to LLMAttributes."""
        # Check that constants exist
        self.assertTrue(hasattr(GenAIAttributes, "SYSTEM"))
        self.assertTrue(hasattr(GenAIAttributes, "OPERATION"))
        self.assertTrue(hasattr(GenAIAttributes, "REQUEST_PROMPT"))

        # Check values match LLMAttributes (aliasing)
        self.assertEqual(GenAIAttributes.SYSTEM, LLMAttributes.SYSTEM)
        self.assertEqual(GenAIAttributes.OPERATION, LLMAttributes.OPERATION)
        self.assertEqual(GenAIAttributes.REQUEST_MODEL, LLMAttributes.REQUEST_MODEL)

        # Check specific string values (wire format changes)
        self.assertEqual(GenAIAttributes.SYSTEM, "llm.system")
        self.assertEqual(GenAIAttributes.REQUEST_PROMPT, "llm.request.prompt")
        self.assertEqual(GenAIAttributes.RESPONSE_TEXT, "llm.response.text")

        # Check mapping of usage tokens
        self.assertEqual(GenAIAttributes.USAGE_INPUT_TOKENS, LLMAttributes.USAGE_PROMPT_TOKENS)
        self.assertEqual(GenAIAttributes.USAGE_OUTPUT_TOKENS, LLMAttributes.USAGE_COMPLETION_TOKENS)

    def test_llm_attributes_completeness(self):
        """Test that LLMAttributes has all required fields."""
        self.assertEqual(LLMAttributes.OPERATION, "llm.operation")
        self.assertEqual(LLMAttributes.REQUEST_PROMPT, "llm.request.prompt")
        self.assertEqual(LLMAttributes.RESPONSE_TEXT, "llm.response.text")
        self.assertEqual(LLMAttributes.USAGE_CACHED_TOKENS, "llm.usage.cached_tokens")

if __name__ == "__main__":
    unittest.main()
