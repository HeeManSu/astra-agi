# Publishing Astra Runtime to PyPI

This guide explains how to publish the Astra Runtime package to PyPI.

## Pre-Publication Checklist

### ✅ Already Complete

- [x] Package structure (`src/astra/`)
- [x] All 58 components exportable
- [x] 16 working examples
- [x] Import tests
- [x] Documentation (embedded README, examples README)

### 📋 Before Publishing

- [ ] Add package README.md (this directory)
- [ ] Review and update pyproject.toml
- [ ] Add/verify LICENSE file
- [ ] Set version number
- [ ] Test build locally
- [ ] Create Git tag for release

---

## Quick Publishing Steps

```bash
# 1. Navigate to runtime package
cd packages/runtime

# 2. Install build tools
uv pip install build twine

# 3. Build the package
python -m build

# 4. Check the build
twine check dist/*

# 5. Upload to TestPyPI (recommended first)
twine upload --repository testpypi dist/*

# 6. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ astra-runtime

# 7. If everything works, upload to PyPI
twine upload dist/*
```

---

## Detailed Steps

### 1. Update `pyproject.toml`

Ensure your `pyproject.toml` has all required metadata:

```toml
[project]
name = "astra-runtime"
version = "0.1.0"  # Semantic versioning
description = "Astra Embedded Runtime - Build AI agents in Python"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}  # or your chosen license
authors = [
    {name = "Your Name", email = "[email protected]"}
]
keywords = ["ai", "agents", "rag", "llm", "framework"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[project.urls]
Homepage = "https://github.com/yourusername/astra"
Documentation = "https://astra-docs.example.com"
Repository = "https://github.com/yourusername/astra"
Issues = "https://github.com/yourusername/astra/issues"
```

### 2. Create Package README.md

Create `packages/runtime/README.md`:

````markdown
# Astra Runtime

Build AI agents in Python with the Astra Embedded Runtime.

## Quick Start

\`\`\`bash
pip install astra-runtime
\`\`\`

\`\`\`python
from astra import Agent, HuggingFaceLocal

agent = Agent(
model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
instructions="You are a helpful assistant"
)

response = await agent.invoke("Hello!")
\`\`\`

## Features

- 🤖 **Agents**: Build intelligent agents with tools and memory
- 📚 **RAG**: Retrieval-Augmented Generation with custom pipelines
- 🗄️ **Storage**: LibSQL and MongoDB backends
- 🛡️ **Guardrails**: PII filtering, content moderation, security
- 🔧 **Tools**: Easy function calling and code execution
- 👥 **Teams**: Multi-agent collaboration

## Documentation

See [examples/](examples/) for 16 comprehensive examples.

## License

[Your License Here]
\`\`\`

### 3. Add LICENSE File

Choose and add a LICENSE file (e.g., MIT, Apache 2.0):

```bash
# Example: MIT License
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2025 [Your Name/Organization]

Permission is hereby granted, free of charge, to any person obtaining a copy...
EOF
```
````

### 4. Set Version

Update version in `pyproject.toml`:

```toml
version = "0.1.0"  # First release
```

Use semantic versioning:

- `0.1.0` - Initial beta release
- `0.2.0` - Minor updates, new features
- `1.0.0` - Production-ready stable release

### 5. Build the Package

```bash
# Install build tools
pip install build twine

# Build distribution packages
python -m build

# This creates:
# - dist/astra_runtime-0.1.0.tar.gz (source)
# - dist/astra_runtime-0.1.0-py3-none-any.whl (wheel)
```

### 6. Verify the Build

```bash
# Check package metadata
twine check dist/*

# Should show: "Checking dist/... PASSED"
```

### 7. Test on TestPyPI (Recommended)

```bash
# Create account at test.pypi.org
# Generate API token

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Install and test
pip install --index-url https://test.pypi.org/simple/ astra-runtime

# Run your import test
python -c "from astra import Agent; print('Success!')"
```

### 8. Publish to PyPI

```bash
# Create account at pypi.org
# Generate API token (Settings → API tokens)

# Configure credentials
cat > ~/.pypirc << EOF
[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE
EOF

# Upload to PyPI
twine upload dist/*
```

### 9. Verify Installation

```bash
# Install from PyPI
pip install astra-runtime

# Test
python -c "from astra import Agent, Tool, Rag; print('✅ Installation successful!')"
```

### 10. Create Git Tag

```bash
# Tag the release
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0

# Create GitHub release from tag
```

---

## Common Issues

### Issue: "File already exists"

**Solution**: Increment version number in `pyproject.toml`, rebuild, and upload new version.

### Issue: Import errors after installation

**Solution**:

- Ensure `framework` package is listed in dependencies
- Check `pyproject.toml` has correct package discovery

### Issue: Missing files in distribution

**Solution**: Add to `pyproject.toml`:

```toml
[tool.setuptools]
packages = ["astra", "astra.embedded"]
package-dir = {"" = "src"}

[tool.setuptools.package-data]
astra = ["py.typed"]
```

---

## Continuous Updates

### Patch Release (Bug fixes)

```bash
# Update version: 0.1.0 → 0.1.1
# Build and upload
python -m build
twine upload dist/*
```

### Minor Release (New features)

```bash
# Update version: 0.1.1 → 0.2.0
# Build and upload
python -m build
twine upload dist/*
```

### Major Release (Breaking changes)

```bash
# Update version: 0.2.0 → 1.0.0
# Document breaking changes
# Build and upload
python -m build
twine upload dist/*
```

---

## Automation with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install build twine

      - name: Build package
        working-directory: packages/runtime
        run: python -m build

      - name: Publish to PyPI
        working-directory: packages/runtime
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

Store PyPI API token as GitHub secret: `PYPI_API_TOKEN`

---

## Status: Ready to Publish! ✅

Your package has:

- ✅ Clean package structure
- ✅ 58 importable components
- ✅ 16 working examples
- ✅ Test coverage
- ✅ Documentation

**Next steps:**

1. Add README.md to this directory
2. Review/update pyproject.toml
3. Add LICENSE file
4. Follow publishing steps above

Once published, users can simply:

```bash
pip install astra-runtime
```
