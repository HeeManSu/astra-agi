import time
import unittest

from observability.semantic import trace_agent, trace_error, trace_llm_call, trace_step, trace_tool


class TestDecoratorBenchmarks(unittest.TestCase):
    def test_benchmark_agent(self):
        @trace_agent(name="BenchAgent", agent_type="react")
        def run(n):
            s = 0
            for i in range(n):
                s += i
            return s
        t0 = time.perf_counter()
        x = run(1000)
        t1 = time.perf_counter()
        self.assertEqual(x, sum(range(1000)))
        _ = (t1 - t0)

    def test_benchmark_tool(self):
        @trace_tool(name="BenchTool")
        def run(a, b):
            return a + b
        t0 = time.perf_counter()
        y = run(3, 5)
        t1 = time.perf_counter()
        self.assertEqual(y, 8)
        _ = (t1 - t0)

    def test_benchmark_llm(self):
        @trace_llm_call(model="gpt-test", prompt_extractor=lambda *a, **k: str(k.get("p", "")))
        def run(p: str):
            return "resp-" + p
        t0 = time.perf_counter()
        z = run(p="hello")
        t1 = time.perf_counter()
        self.assertEqual(z, "resp-hello")
        _ = (t1 - t0)

    def test_benchmark_step(self):
        @trace_step("Execute", "Run heavy task")
        def run(n):
            return n * 2
        t0 = time.perf_counter()
        r = run(21)
        t1 = time.perf_counter()
        self.assertEqual(r, 42)
        _ = (t1 - t0)

    def test_benchmark_error(self):
        @trace_error()
        def run():
            raise RuntimeError("boom")
        t0 = time.perf_counter()
        with self.assertRaises(RuntimeError):
            run()
        t1 = time.perf_counter()
        _ = (t1 - t0)

if __name__ == "__main__":
    unittest.main()
