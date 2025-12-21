from typing import List
from observability.instrumentation.core.registry import InstrumentationRegistry, InstrumentorSpec

def register_builtin_providers(registry: InstrumentationRegistry) -> None:
    """
    Register all built-in provider instrumentors.
    
    This function serves as the central catalog for all supported LLM providers.
    To add a new provider (e.g., AWS Bedrock), add its specification here.
    """
    
    # Google GenAI
    registry.register(
        package_name="google.genai",
        spec=InstrumentorSpec(
            module_path="observability.instrumentation.providers.google_genai.instrumentor",
            class_name="GoogleGenAIInstrumentor",
            min_version="0.1.0",
            priority=10,
        ),
    )
    registry.register(
        package_name="google.genai.aio",
        spec=InstrumentorSpec(
            module_path="observability.instrumentation.providers.google_genai.instrumentor",
            class_name="GoogleGenAIInstrumentor",
            min_version="0.1.0",
            priority=10,
        ),
    )
    
    # AWS Bedrock (Placeholder for future implementation)
    # registry.register(
    #     package_name="boto3",
    #     spec=InstrumentorSpec(
    #         module_path="observability.instrumentation.providers.aws_bedrock.instrumentor",
    #         class_name="AWSBedrockInstrumentor",
    #         min_version="1.0.0",
    #         priority=10,
    #     ),
    # )
