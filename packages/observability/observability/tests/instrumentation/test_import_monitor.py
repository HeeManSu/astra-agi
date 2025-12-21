import sys
import types
import unittest
from unittest.mock import patch

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from observability.instrumentation.core.registry import InstrumentationRegistry, InstrumentorSpec
from observability.instrumentation.core.import_monitor import ImportMonitor
from observability.instrumentation.core.version_checker import VersionChecker
from observability.instrumentation.core.base_instrumentor import InstrumentorConfig


class _MemoryExporter(SpanExporter):
    def __init__(self):
        self.spans = []
    def export(self, spans) -> "SpanExportResult":  # type: ignore[override]
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS
    def shutdown(self) -> None:
        pass


class TestImportMonitor(unittest.TestCase):
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
                        self.text = "hello world"
                        class Meta:
                            prompt_token_count = 3
                            candidates_token_count = 2
                            total_token_count = 5
                            cached_content_token_count = None
                        self.usage_metadata = Meta()
                return Resp()
            def generate_content_stream(self, model, contents, config=None):
                class Chunk:
                    def __init__(self, text):
                        self.text = text
                for t in ["hi ", "there"]:
                    yield Chunk(t)
            def count_tokens(self, model, contents):
                class C:
                    total_tokens = 7
                return C()
            def compute_tokens(self, model, contents):
                class TI:
                    def __init__(self, ids):
                        self.token_ids = ids
                class R:
                    tokens_info = [TI([1,2,3])]
                return R()
        models_mod.Models = Models
        models_mod.__version__ = "0.1.1"

        genai_mod = types.ModuleType("google.genai")
        genai_mod.__version__ = "0.1.1"

        sys.modules["google"] = types.ModuleType("google")
        sys.modules["google.genai"] = genai_mod
        sys.modules["google.genai.models"] = models_mod

        self.registry = InstrumentationRegistry()
        self.registry.register(
            "google.genai",
            InstrumentorSpec(
                module_path="observability.instrumentation.providers.google_genai.instrumentor",
                class_name="GoogleGenAIInstrumentor",
                min_version="0.1.0",
                priority=10,
            ),
        )

        self.monitor = ImportMonitor(
            registry=self.registry,
            version_checker=VersionChecker(),
            config=InstrumentorConfig(),
        )
        self.monitor.instrument_already_imported()

    def tearDown(self):
        self._get_tracer_patch.stop()
        self._third_party_patch.stop()
        for name in ["google.genai", "google.genai.models", "google"]:
            sys.modules.pop(name, None)

    def _find_exported_span(self, name: str):
        for span in self.exporter.spans:
            if span.name == name:
                return span
        return None

    def test_generate_content_sync_span_attributes(self):
        from google.genai.models import Models
        m = Models()
        resp = m.generate_content(model="gemini-2.5-flash", contents="Say hi", config={"temperature": 0.2, "max_output_tokens": 64})
        self.assertEqual(getattr(resp, "text", ""), "hello world")
        span = self._find_exported_span("generate_content.client")
        self.assertIsNotNone(span)
        attrs = span.attributes
        self.assertEqual(attrs.get("genai.request.model"), "gemini-2.5-flash")
        self.assertEqual(attrs.get("genai.request.temperature"), 0.2)
        self.assertEqual(attrs.get("genai.request.max_tokens"), 64)
        self.assertEqual(attrs.get("genai.response.text"), "hello world")
        self.assertEqual(attrs.get("genai.usage.total_tokens"), 5)

    def test_generate_content_stream_sync(self):
        from google.genai.models import Models
        m = Models()
        chunks = list(m.generate_content_stream(model="gemini", contents="stream me"))
        self.assertEqual("".join([c.text for c in chunks]), "hi there")
        span = self._find_exported_span("generate_content_stream.client")
        self.assertIsNotNone(span)
        attrs = span.attributes
        self.assertEqual(attrs.get("genai.response.text"), "hi there")

    def test_count_tokens_sync(self):
        from google.genai.models import Models
        m = Models()
        resp = m.count_tokens(model="gemini", contents="abc")
        self.assertEqual(getattr(resp, "total_tokens", None), 7)
        span = self._find_exported_span("count_tokens.client")
        self.assertIsNotNone(span)
        attrs = span.attributes
        self.assertEqual(attrs.get("genai.usage.total_tokens"), 7)

    def test_compute_tokens_sync(self):
        from google.genai.models import Models
        m = Models()
        resp = m.compute_tokens(model="gemini", contents="abc")
        self.assertTrue(hasattr(resp, "tokens_info"))
        span = self._find_exported_span("compute_tokens.client")
        self.assertIsNotNone(span)
        attrs = span.attributes
        self.assertEqual(attrs.get("genai.usage.total_tokens"), 3)


if __name__ == "__main__":
    unittest.main()

