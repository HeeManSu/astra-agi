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

class TestStreamingTokens(unittest.TestCase):
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
        class MetaA:
            prompt_token_count = 3
            candidates_token_count = None
            total_token_count = 3
            cached_content_token_count = None
        class MetaB:
            prompt_token_count = None
            candidates_token_count = 5
            total_token_count = 8
            cached_content_token_count = None
        class ChunkA:
            def __init__(self):
                self.text = "hello "
                self.usage_metadata = MetaA()
        class ChunkB:
            def __init__(self):
                self.text = "world"
                self.usage_metadata = MetaB()
        class CountResp:
            def __init__(self, n):
                self.total_tokens = n
        class Models:
            def generate_content_stream(self, model, contents, config=None):
                yield ChunkA()
                yield ChunkB()
            def count_tokens(self, model, contents):
                if contents == "prompt":
                    return CountResp(4)
                if contents == "hello world":
                    return CountResp(6)
                return CountResp(1)
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

    def _find_span(self, name: str):
        for s in self.exporter.spans:
            if s.name == name:
                return s
        return None

    def test_streaming_usage_aggregation(self):
        from google.genai.models import Models
        m = Models()
        chunks = list(m.generate_content_stream(model="gemini", contents="prompt"))
        self.assertEqual("".join([c.text for c in chunks]), "hello world")
        span = self._find_span("generate_content_stream.client")
        self.assertIsNotNone(span)
        attrs = span.attributes
        self.assertEqual(attrs.get("genai.response.text"), "hello world")
        self.assertEqual(attrs.get("genai.usage.input_tokens"), 3)
        self.assertEqual(attrs.get("genai.usage.output_tokens"), 5)
        self.assertEqual(attrs.get("genai.usage.total_tokens"), 8)

    def test_streaming_usage_fallback_count_tokens(self):
        for name in ["google.genai", "google.genai.models", "google"]:
            sys.modules.pop(name, None)
        models_mod = types.ModuleType("google.genai.models")
        class ModelsNoUsage:
            def generate_content_stream(self, model, contents, config=None):
                class C:
                    def __init__(self, t):
                        self.text = t
                yield C("foo ")
                yield C("bar")
            def count_tokens(self, model, contents):
                if contents == "prompt":
                    class R:
                        total_tokens = 2
                    return R()
                if contents == "foo bar":
                    class R:
                        total_tokens = 3
                    return R()
                class R:
                    total_tokens = 0
                return R()
        models_mod.Models = ModelsNoUsage
        models_mod.__version__ = "0.1.1"
        genai_mod = types.ModuleType("google.genai")
        genai_mod.__version__ = "0.1.1"
        sys.modules["google"] = types.ModuleType("google")
        sys.modules["google.genai"] = genai_mod
        sys.modules["google.genai.models"] = models_mod

        registry = InstrumentationRegistry()
        registry.register(
            "google.genai",
            InstrumentorSpec(
                module_path="observability.instrumentation.providers.google_genai.instrumentor",
                class_name="GoogleGenAIInstrumentor",
                min_version="0.1.0",
                priority=10,
            ),
        )
        monitor = ImportMonitor(
            registry=registry,
            version_checker=VersionChecker(),
            config=InstrumentorConfig(),
        )
        monitor.instrument_already_imported()

        m = models_mod.Models()
        chunks = list(m.generate_content_stream(model="gemini", contents="prompt"))
        self.assertEqual("".join([c.text for c in chunks]), "foo bar")
        span = self._find_span("generate_content_stream.client")
        self.assertIsNotNone(span)
        attrs = span.attributes
        self.assertEqual(attrs.get("genai.response.text"), "foo bar")
        self.assertEqual(attrs.get("genai.usage.input_tokens"), 2)
        self.assertEqual(attrs.get("genai.usage.output_tokens"), 3)
        self.assertEqual(attrs.get("genai.usage.total_tokens"), 5)

if __name__ == "__main__":
    unittest.main()
