import unittest
from unittest.mock import patch, MagicMock
from observability.semantic import trace_agent

class TestTraceAgent(unittest.TestCase):
    def setUp(self):
        self.mock_span = MagicMock()
        self.mock_ctx = MagicMock()
        self.start_patch = patch("observability.semantic.agent.start_span", return_value=(self.mock_ctx, self.mock_span))
        self.end_patch = patch("observability.semantic.agent.end_span")
        self.mock_start = self.start_patch.start()
        self.end_patch.start()

    def tearDown(self):
        self.start_patch.stop()
        self.end_patch.stop()

    def test_sync_agent_span(self):
        @trace_agent(name="Planner", agent_type="react", thread_id="t1", conversation_id="c1")
        def run():
            return "ok"
        res = run()
        self.assertEqual(res, "ok")
        args, kwargs = self.mock_start.call_args
        self.assertEqual(args[0], "agent.run")
        attrs = args[1]
        self.assertEqual(attrs["agent.name"], "Planner")
        self.assertEqual(attrs["agent.type"], "react")
        self.assertEqual(attrs["agent.thread_id"], "t1")
        self.assertEqual(attrs["agent.conversation_id"], "c1")

if __name__ == "__main__":
    unittest.main()
