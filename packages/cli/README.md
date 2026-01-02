# Astra CLI

> **Code-generation + Project Management for Astra Servers**

The Astra CLI is a powerful tool designed to scaffold, evolve, and manage Astra server projects. It acts as a **project mutator**, generating high-quality boilerplate code and ensuring project consistency over time via a state-driven approach.

---

## 📋 Requirements

- **Python**: 3.10+
- **Pip**: Latest version
- **OS**: Cross-platform (Linux, macOS, Windows)

---

## 🛠️ Installation

### From PyPI (Recommended)

```bash
pip install astra-cli
astra --help
```

### From Source

```bash
cd packages/cli
pip install -e .
astra --help
```

---

## 🧠 Mental Model

```
astra-cli = create + evolve Astra server projects
```

- **Project Scaffolder + Mutator**: Generates server projects and modifies code to add/remove features.
- **State-Driven**: Keeps project consistent over time via `astra.json` state.
- **Registry-Based**: Features are defined declaratively in a Python dictionary.

---

## 🏗️ Architecture (HLD)

The CLI follows a **layered architecture** to separate concerns:

1.  **Command Layer** (User Interface): Parses commands (Typer).
2.  **Engine Layer** (Logic):
    - **Project Engine**: Loads/saves state (`astra.json`), validates schema.
    - **Feature Engine**: Resolves keys (e.g., `auth-jwt`), validates against registry, builds _FeaturePlans_.
    - **Template Engine**: Renders Jinja2 templates, performs safe File I/O (rollback/txn).
    - **Dependency Engine**: Merges dependencies into `pyproject.toml`.
3.  **Registry Layer** (Data): Defines features, files, and dependencies `Feature → Files → Deps`.

```
┌──────────────────────────────────────────┐
│           Command Layer (CLI)            │
│              Typer-based                 │
└─────────────┬────────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
    ▼         ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Project │ │Feature │ │Template│ │  Deps  │
│Engine  │ │Engine  │ │Engine  │ │Engine  │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │          │          │          │
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│astra.  │ │Feature │ │  File  │ │project.│
│json    │ │Registry│ │ System │ │toml    │
└────────┘ └────────┘ └────────┘ └────────┘
```

### 🔄 Control Flow: `astra add ui`

```
astra add ui
   │
   ▼
[ Project Discovery ]
   └─ find astra.json (walk up directory tree)
   │
   ▼
[ Project Engine ]
   └─ load & validate state
   │
   ▼
[ Feature Engine ]
   └─ read registry
   └─ build change plan (FeaturePlan)
   │
   ▼
[ Template Engine ]
   └─ render new files
   └─ modify existing files (patches)
   │
   ▼
[ Dependency Engine ]
   └─ update pyproject.toml / requirements.txt
   │
   ▼
[ Project Engine ]
   └─ update & save astra.json
```

---

## 📂 Registry Layer

The Registry is the heart of the CLI. It maps feature keys to specific templates and dependencies.

```python
# templates/registry.py
FEATURES = {
    "core": {
        "always": True,
        "files": ["main.py.j2", "settings.py.j2", ...],
    },
    "auth-jwt": {
        "files": ["auth/jwt.py.j2", "auth/middleware.py.j2"],
        "deps": ["python-jose[cryptography]"],
        "conflicts": ["auth-api-key"]
    },
    "rate-limit": {
        "files": ["middleware/rate_limit.py.j2"],
        "patches": ["patches/main_add_rate_limit.py.j2"], # Patch support
        "deps": ["slowapi"],
    }
}
```

---

## 📝 State Management (`astra.json`)

Each project maintains its own state. The CLI finds the active project by walking up the directory tree from the current working directory.

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "sales-ai",
    "type": "server"
  },
  "features": {
    "core": true,
    "auth": "jwt",
    "rate-limit": true
  },
  "runtime": {
    "entrypoint": "app.main:app"
  }
}
```

**Project Discovery**: CLI walks up from current directory looking for `astra.json`. If not found:

```
ERROR: No Astra project found in this directory or parents.
TIP: Run `astra init server` to create one.
```

---

## 🚀 Commands & Workflows

### 1. `astra init server`

Scaffolds a new project interactively or via flags.

- **Flow**: User Input → Template Render → State Create.

### 2. `astra add <feature>`

Adds capability to an existing project.

- **Checks**: Is feature valid? Are dependencies installed?
- **Action**: Renders templates, updates `pyproject.toml`, updates `astra.json`.

### 3. `astra remove <feature>`

Safely removes a feature.

- **Safety**: Checks if dependencies are shared by other features before removing.
- **Cleanup**: Removes empty directories.

### 4. `astra sync`

State → Code Reconciliation. Corrects drift.

```
astra sync
   │
   ▼
[ Load astra.json ]
   │
   ▼
[ Validate schema + features ]
   │
   ▼
[ Feature Engine ]
   └─ resolve expected files
   │
   ▼
[ Template Engine ]
   └─ add missing files only
   └─ skip existing files (never overwrites)
   │
   ▼
[ Report result ]
```

- **Use Case**: Upgrading CLI version, restoring missing files, fixing schema mismatch.
- **Safety**: Never overwrites existing user files by default.

---

## ⚠️ Edge Case Handling

| Case                        | Expected Behavior                                                      |
| :-------------------------- | :--------------------------------------------------------------------- |
| **Command outside project** | `ERROR: No Astra project found.` + Tip: Run `astra init`               |
| **Partial Failure**         | **Rollback**: Filesystem is restored, `astra.json` not updated.        |
| **Feature already enabled** | **No-op**: Friendly warning, zero side-effects.                        |
| **Remove non-existent**     | **Safe No-op**: Warning message.                                       |
| **Remove `core`**           | **Hard Error**: Core feature is protected.                             |
| **Registry mismatch**       | Validation error + Tip: Run `astra sync`.                              |
| **Cross-feature conflict**  | (e.g. JWT vs API Key) Error + Tip to remove conflicting feature first. |
| **Schema Mismatch**         | `WARN: Schema v0.9 detected` + Tip: Run `astra sync`.                  |

### Example Error Messages

```
ERROR: Unknown feature "uui"
Valid features:
  - ui
  - rate-limit
  - observability-logs
TIP: Fix astra.json or run `astra add ui`
```

```
WARN: astra.json schema v0.9 detected (CLI supports v1.0)
TIP: Run `astra sync` to upgrade safely.
```

---

## ✅ Testing Strategy

We maintain a rigorous test suite of **107 tests** with **~88% coverage**.

### 🧪 Run All Tests

```bash
uv run pytest
```

### Detailed Test Checklist

#### **Unit Tests (59 Tests)**

- [x] **Project Engine**: Discovery mechanism, Schema validation, JSON loading/saving.
- [x] **Feature Engine**: Feature validation, Conflict detection, Plan generation.
- [x] **Dependency Engine**: TOML parsing, Duplicate detection, Version handling.
- [x] **Registry Integrity**:
  - [x] No missing files/deps keys.
  - [x] All templates exist on disk.
  - [x] No duplicate files across features.
- [x] **Config Corruption**:
  - [x] Handle null features.
  - [x] Handle malformed JSON.
  - [x] Handle missing required fields.
- [x] **Shared Dependencies**: Dependencies preserved if used by other features.
- [x] **Dev Command**: Entrypoint resolution, command construction.

#### **Integration Tests (37 Tests)**

- [x] **Templates**: Jinja rendering, File permissions, Nested directories.
- [x] **Dry-Run Accuracy**:
  - [x] **Critical**: Verify timestamp unchanged (0 filesystem touches).
  - [x] Output completeness (shows all files/deps to be changed).
- [x] **Partial Removal**:
  - [x] Preserves user files in feature directories.
  - [x] Cleans up empty directories.
  - [x] Idempotency (Repeat commands safely).

#### **E2E Tests (11 Tests)**

- [x] **Init Workflow**: Full project create + auth.
- [x] **Add/Remove Cycle**: Add feature -> Remove feature -> Add again.
- [x] **Sync Workflow**: Delete file -> Sync -> File restored.

---

## 📦 Publishing to PyPI

### Prerequisites

```bash
pip install build twine
```

### Build Distribution

```bash
cd packages/cli
python -m build
```

This creates:

- `dist/astra_cli-0.1.0-py3-none-any.whl` (wheel)
- `dist/astra-cli-0.1.0.tar.gz` (source)

### Test on TestPyPI (Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ astra-cli
```

### Publish to PyPI

```bash
# Upload to production PyPI
twine upload dist/*

# Users can now install
pip install astra-cli
```

### Automated Publishing (GitHub Actions)

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
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: |
          pip install build twine
      - name: Build package
        run: |
          cd packages/cli
          python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          twine upload packages/cli/dist/*
```

**Setup**:

1. Create PyPI API token at https://pypi.org/manage/account/token/
2. Add token to GitHub Secrets as `PYPI_API_TOKEN`
3. Create a GitHub Release to trigger automated publishing

---

## 🔮 Future Scope

- **Remote Templates**: Fetch from GitHub/S3.
- **Plugin System**: User-defined local feature registry.
- **Cloud Deploy**: `astra cloud deploy` interactions.
- **GUI**: Web-based project manager.
- **Migration Tools**: Automated code migration for framework upgrades.
