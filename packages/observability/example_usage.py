from google import genai
from observability.client import Client as ObservabilityClient


# Initialize Observability Client
# This will automatically instrument supported libraries like google-genai
# Set endpoint="console" to see traces in stdout without needing an OTLP collector
obs_client = ObservabilityClient(
    service_name="example-usage",
    enable_tracing=True,
    endpoint="json"
)

# Initialize client with API key
client = genai.Client(api_key="AIzaSyAV1j9MvjDjYYJGnesrrslJvISwIcAvSZs")

# Generate content
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Give me content idea for tech based youtube channel"
)

print("Gemini Response:")
