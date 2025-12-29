import unittest
from unittest.mock import patch, MagicMock
from observability.semantic import trace_llm_call
from observability.semantic.conventions import LLMAttributes, GenAIAttributes

class TestTraceLLM(unittest.TestCase):
    def setUp(self):
        self.mock_span = MagicMock()
        self.mock_ctx = MagicMock()
        self.start_patch = patch("observability.semantic.llm.start_span", return_value=(self.mock_ctx, self.mock_span))
        self.end_patch = patch("observability.semantic.llm.end_span")
        self.set_patch = patch("observability.semantic.llm.set_attributes")
        self.trunc_patch = patch("observability.semantic.llm.truncate_text", side_effect=lambda s, l: s[:l])
        self.mock_start = self.start_patch.start()
        self.end_patch.start()
        self.set_patch.start()
        self.trunc_patch.start()

    def tearDown(self):
        self.start_patch.stop()
        self.end_patch.stop()
        self.set_patch.stop()
        self.trunc_patch.stop()

    def test_sync_llm_span(self):
        @trace_llm_call(model="gpt-4", temperature=0.7, max_tokens=128, prompt_extractor=lambda *a, **k: str(k.get("prompt", "")), response_extractor=lambda r: r)
        def run(prompt: str):
            return "response"
        result = run(prompt="hello")
        self.assertEqual(result, "response")
        args, kwargs = self.mock_start.call_args
        attrs = args[1]
        self.assertEqual(attrs[LLMAttributes.REQUEST_MODEL], "gpt-4")
        self.assertEqual(attrs[LLMAttributes.REQUEST_TEMPERATURE], 0.7)
        self.assertEqual(attrs[LLMAttributes.REQUEST_MAX_TOKENS], 128)

if __name__ == "__main__":
    unittest.main()
