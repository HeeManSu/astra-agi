
import unittest

from observability.instrumentation.core.registry import InstrumentationRegistry, InstrumentorSpec


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = InstrumentationRegistry()

    def test_register_and_get(self):
        """Test basic registration and retrieval."""
        spec = InstrumentorSpec(
            module_path="observability.instrumentation.providers.test.instrumentor",
            class_name="TestInstrumentor",
            min_version="1.0.0"
        )

        self.registry.register("test-package", spec)

        retrieved = self.registry.get_spec("test-package")
        self.assertEqual(retrieved, spec)

    def test_get_nonexistent(self):
        """Test retrieving a package that isn't registered."""
        self.assertIsNone(self.registry.get_spec("ghost-package"))

    def test_conflict_resolution(self):
        """Test that higher priority specs override lower ones."""
        low_prio = InstrumentorSpec(
            module_path="mod.low",
            class_name="Low",
            priority=0
        )
        high_prio = InstrumentorSpec(
            module_path="mod.high",
            class_name="High",
            priority=100
        )

        self.registry.register("conflict-pkg", low_prio)
        self.registry.register("conflict-pkg", high_prio)

        result = self.registry.get_spec("conflict-pkg")
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.class_name, "High")

if __name__ == "__main__":
    unittest.main()
