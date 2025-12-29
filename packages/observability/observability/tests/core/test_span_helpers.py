
import unittest
from unittest.mock import MagicMock, patch

from observability.core.span_helpers import (
    set_span_attributes,
    start_span,
    trace_span,
)


class TestSpanHelpers(unittest.TestCase):
    def setUp(self):
        self.mock_tracer = MagicMock()
        self.mock_span = MagicMock()
        self.mock_tracer.start_as_current_span.return_value.__enter__.return_value = self.mock_span

        self.patcher = patch("observability.core.span_helpers._get_tracer", return_value=self.mock_tracer)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_trace_span_decorator(self):
        """Test the @trace_span decorator."""

        @trace_span(name="test_func", attributes={"key": "value"})
        def sample_function(arg):
            return f"processed {arg}"

        result = sample_function("data")

        self.assertEqual(result, "processed data")
        self.mock_tracer.start_as_current_span.assert_called_with("test_func")
        self.mock_span.set_attributes.assert_called_with({"key": "value"})

    def test_trace_span_decorator_exception(self):
        """Test decorator handles exceptions correctly."""

        @trace_span()
        def failing_function():
            raise ValueError("oops")

        with self.assertRaises(ValueError):
            failing_function()

        # Should record exception on span
        self.mock_span.record_exception.assert_called()
        self.mock_span.set_status.assert_called()

    def test_start_span_context_manager(self):
        """Test start_span context manager."""
        with start_span("manual_span", {"attr": "1"}) as span:
            span.set_attribute("inner", "val")

        self.mock_tracer.start_as_current_span.assert_called_with("manual_span", attributes={"attr": "1"})

    @patch("observability.core.span_helpers.trace.get_current_span")
    def test_set_span_attributes(self, mock_get_current):
        """Test helper to set attributes on active span."""
        mock_active_span = MagicMock()
        mock_get_current.return_value = mock_active_span

        set_span_attributes({"new_key": "new_val"})

        mock_active_span.set_attributes.assert_called_with({"new_key": "new_val"})

if __name__ == "__main__":
    unittest.main()
