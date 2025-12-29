import unittest
from unittest.mock import patch, MagicMock
from observability.semantic import trace_tool

class TestTraceTool(unittest.TestCase):
    def setUp(self):
        self.mock_span = MagicMock()
        self.mock_ctx = MagicMock()
        self.start_patch = patch("observability.semantic.tool.start_span", return_value=(self.mock_ctx, self.mock_span))
        self.end_patch = patch("observability.semantic.tool.end_span")
        self.set_patch = patch("observability.semantic.tool.set_attributes")
        self.mock_start = self.start_patch.start()
        self.end_patch.start()
        self.set_patch.start()

    def tearDown(self):
        self.start_patch.stop()
        self.end_patch.stop()
        self.set_patch.stop()

    def test_sync_tool_span(self):
        @trace_tool(name="search")
        def run(q, api_key=None):
            return {"result": "ok"}
        res = run("hello", api_key="secret-token")
        self.assertEqual(res["result"], "ok")
        args, kwargs = self.mock_start.call_args
        self.assertTrue(args[0].startswith("tool.search"))

if __name__ == "__main__":
    unittest.main()
