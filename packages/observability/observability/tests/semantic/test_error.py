import unittest
from unittest.mock import MagicMock, patch

from observability.semantic import trace_error


class TestTraceError(unittest.TestCase):
    def setUp(self):
        self.mock_span = MagicMock()
        self.get_patch = patch("opentelemetry.trace.get_current_span", return_value=self.mock_span)
        self.get_patch.start()

    def tearDown(self):
        self.get_patch.stop()

    def test_error_attributes_set(self):
        @trace_error()
        def run():
            raise ValueError("bad")
        with self.assertRaises(ValueError):
            run()
        self.mock_span.record_exception.assert_called()
        self.mock_span.set_attribute.assert_any_call("error.type", "ValueError")
        self.mock_span.set_attribute.assert_any_call("error.message", "bad")

if __name__ == "__main__":
    unittest.main()
