import json

import boto3
from observability.client import Client as ObservabilityClient


# User provided API Key
# Note: AWS Bedrock typically uses AWS Access Key ID and Secret Access Key via IAM.
# This key is included as requested.
API_KEY = "ABSKQmVkcm9ja0FQSUtleS0xNHAxLWF0LTA0Njc2MzQ3MzM3MDpoTUpIRENERHBRRUlkTjVRTk9NM0p6UENQZ0MwSmoyaXR1RTEyUm1IZVd2LzZudGN6TVIzY2cvYW95RT0="

# Initialize Observability Client
# This will automatically instrument supported libraries like boto3
obs_client = ObservabilityClient(
    service_name="bedrock-nova-example",
    enable_tracing=True,
    endpoint="console"
)

# Initialize Bedrock Runtime Client
# Ensure your environment is configured with AWS credentials (e.g., ~/.aws/credentials)
client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

# Amazon Nova Pro Model ID
model_id = "amazon.nova-pro-v1:0"

# Request body for Nova models
# Nova uses the converse API structure but via invoke_model requires specific JSON structure:
# {
#   "system": [{"text": "..."}],
#   "messages": [{"role": "...", "content": [{"text": "..."}]}],
#   "inferenceConfig": {...}
# }
request_body = {
    "system": [{"text": "You are a creative content generator."}],
    "messages": [
        {
            "role": "user",
            "content": [{"text": "Give me content idea for tech based youtube channel"}]
        }
    ],
    "inferenceConfig": {
        "maxTokens": 1000,
        "temperature": 0.7,
        "topP": 0.9
    }
}

print(f"Invoking model: {model_id}")

try:
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )

    # Parse Nova response
    body_bytes = response["body"].read()
    response_json = json.loads(body_bytes)

    # Extract content from Nova's specific response structure
    # Structure: output -> message -> content -> list of items
    content_text = ""
    if "output" in response_json:
        message = response_json["output"]["message"]
        if "content" in message:
            for item in message["content"]:
                if "text" in item:
                    content_text += item["text"]

    print("\nNova Pro Response:")
    print(content_text)

except Exception as e:
    print(f"Error invoking model: {e}")
