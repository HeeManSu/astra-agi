import unittest
from unittest.mock import MagicMock, patch

from observability.semantic import trace_step


class TestTraceStep(unittest.TestCase):
    def setUp(self):
        self.mock_span = MagicMock()
        self.mock_ctx = MagicMock()
        self.start_patch = patch("observability.semantic.step.start_span", return_value=(self.mock_ctx, self.mock_span))
        self.end_patch = patch("observability.semantic.step.end_span")
        self.mock_start = self.start_patch.start()
        self.end_patch.start()

    def tearDown(self):
        self.start_patch.stop()
        self.end_patch.stop()

    def test_sync_step_span(self):
        @trace_step("Plan", step_purpose="Outline approach")
        def run():
            return 1
        x = run()
        self.assertEqual(x, 1)
        args, kwargs = self.mock_start.call_args
        attrs = args[1]
        self.assertEqual(attrs["step.name"], "Plan")
        self.assertEqual(attrs["step.purpose"], "Outline approach")

if __name__ == "__main__":
    unittest.main()
