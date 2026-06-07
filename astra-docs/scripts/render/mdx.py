"""IR -> MDX rendering via Jinja2.

The Jinja environment is configured with autoescape disabled (we're emitting
MDX, not HTML) and trims/lstrips blocks so the templates can be readable
without leaking whitespace into the output.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .ir import ClassIR, FuncIR, ModuleIR
from .xref import XrefIndex


def _make_env(templates_dir: Path, xref: XrefIndex) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )

    def _escape_mdx(text: str) -> str:
        # MDX treats `{` and `}` as JSX expression delimiters. Escape any
        # naked braces in plain prose.
        if not text:
            return ""
        return text.replace("{", "\\{").replace("}", "\\}")

    env.filters["mdx_escape"] = _escape_mdx
    env.filters["linkify_type"] = xref.linkify

    def _bool_js(value: object) -> str:
        return "true" if value else "false"

    env.filters["js_bool"] = _bool_js
    return env


class Renderer:
    """Render :class:`ModuleIR` instances into MDX files."""

    def __init__(self, templates_dir: Path, xref: XrefIndex) -> None:
        self.env = _make_env(templates_dir, xref)
        self.xref = xref

    def render_module(self, module: ModuleIR, package: str) -> str:
        tpl = self.env.get_template("module.mdx.j2")
        return tpl.render(module=module, package=package)

    def render_class(self, cls: ClassIR) -> str:
        tpl = self.env.get_template("class.mdx.j2")
        return tpl.render(cls=cls)

    def render_function(self, func: FuncIR) -> str:
        tpl = self.env.get_template("function.mdx.j2")
        return tpl.render(func=func)

    def write_module(self, module: ModuleIR, out_dir: Path, package: str) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        # Use the module's leaf name; e.g. ``astra.agents`` -> ``agents.mdx``.
        leaf = module.qualname.split(".")[-1]
        path = out_dir / f"{leaf}.mdx"
        path.write_text(self.render_module(module, package))
        return path
