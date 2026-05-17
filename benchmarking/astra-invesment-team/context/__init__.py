from pathlib import Path


CONTEXT_DIR = Path(__file__).parent


def load_context(files: list[str]) -> str:
    sections = []
    for file in files:
        path = CONTEXT_DIR / file
        if path.exists():
            sections.append(path.read_text())
    return "\n\n---\n\n".join(sections)
