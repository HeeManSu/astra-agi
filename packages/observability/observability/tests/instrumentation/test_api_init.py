import sys
import types
import unittest
from unittest.mock import patch

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from observability import Observability
from observability.instrumentation import shutdown as instrumentation_shutdown
from observability.instrumentation.core.base_instrumentor import InstrumentorConfig


class _MemoryExporter(SpanExporter):
    def __init__(self):
        self.spans = []
    def export(self, spans) -> "SpanExportResult":  # type: ignore[override]
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS
    def shutdown(self) -> None:
        pass


class TestApiInit(unittest.TestCase):
    def setUp(self):
        provider = TracerProvider()
        self.exporter = _MemoryExporter()
        provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self._tracer = provider.get_tracer("observability.instrumentation")
        self._get_tracer_patch = patch("observability.instrumentation.common.span_management.get_tracer", return_value=self._tracer)
        self._get_tracer_patch.start()
        self._third_party_patch = patch("observability.instrumentation.core.import_monitor._is_third_party_module", return_value=True)
        self._third_party_patch.start()

        models_mod = types.ModuleType("google.genai.models")
        class Models:
            def generate_content(self, model, contents, config=None):
                class Resp:
                    def __init__(self):
                        self.text = "content idea response"
                        class Meta:
                            prompt_token_count = 6
                            candidates_token_count = 10
                            total_token_count = 16
                            cached_content_token_count = None
                        self.usage_metadata = Meta()
                return Resp()
        models_mod.Models = Models
        models_mod.__version__ = "0.1.1"

        genai_mod = types.ModuleType("google.genai")
        class Client:
            def __init__(self, api_key=None):
                self.models = Models()
        genai_mod.Client = Client
        genai_mod.__version__ = "0.1.1"

        sys.modules["google"] = types.ModuleType("google")
        sys.modules["google.genai"] = genai_mod
        sys.modules["google.genai.models"] = models_mod

    def tearDown(self):
        instrumentation_shutdown()
        self._get_tracer_patch.stop()
        self._third_party_patch.stop()
        for name in ["google.genai", "google.genai.models", "google"]:
            sys.modules.pop(name, None)

    def test_Observability_init_instruments_and_traces(self):
        Observability.init(service_name="demo", endpoint="console")

        from google import genai
        client = genai.Client(api_key="fake")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Give me content idea for tech based youtube channel",
        )
        print("Gemini Response:")
        print(response.text)

        spans = [s for s in self.exporter.spans if s.name == "generate_content.client"]
        self.assertTrue(len(spans) >= 1)
        span = spans[-1]
        attrs = span.attributes
        self.assertEqual(attrs.get("genai.request.model"), "gemini-2.5-flash")
        self.assertEqual(attrs.get("genai.response.text"), "content idea response")
        self.assertEqual(attrs.get("genai.usage.total_tokens"), 16)


if __name__ == "__main__":
    unittest.main()

