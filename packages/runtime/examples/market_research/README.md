# Market Research Agent Example

This example demonstrates how to create a market research agent using **inbuilt packages** from the codebase (not published packages).

## Key Differences from Published Package Version

- Uses `sys.path` manipulation to import from local framework and runtime packages
- Imports directly from `framework.*` modules instead of `astra.*`
- No need to install published packages - uses inbuilt code

## Setup

1. **Install dependencies** (if not already installed):

```bash
cd packages/runtime
pip install -e ".[mongodb,aws]"
```

2. **Set environment variables**:

```bash
# AWS credentials for Bedrock
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-south-1

# MongoDB connection (optional, defaults to localhost)
export MONGODB_URL=mongodb://localhost:27017

# ScrapingDog API key (optional, has fallback)
export SCRAPINGDOG_API_KEY=your_key
```

## Running

### Option 1: Direct Python execution

```bash
cd packages/runtime
python examples/market_research/main.py
```

### Option 2: As module

```bash
cd packages/runtime
python -m examples.market_research.main
```

### Option 3: With uvicorn

```bash
cd packages/runtime
uvicorn examples.market_research.main:app --reload --host 127.0.0.1 --port 8000
```

## Access Points

- **API**: http://127.0.0.1:8000/api
- **Playground**: http://127.0.0.1:8000/playground
- **Docs**: http://127.0.0.1:8000/docs

## Troubleshooting

### Import Errors

If you see import errors, ensure:

1. You're running from `packages/runtime/` directory
2. Framework package is in the workspace
3. All dependencies are installed

### MongoDB Connection Errors

If MongoDB is not running:

- Install and start MongoDB locally, OR
- Use a cloud MongoDB instance and update `MONGODB_URL`

### AWS Bedrock Errors

Ensure:

- AWS credentials are configured
- Region supports the model (`amazon.apac.nova.pro`)
- Model ID is correct for your region

## Files

- `main.py` - Main server setup and agent creation
- `tools.py` - Amazon scraping tools using ScrapingDog API
- `__init__.py` - Package marker
