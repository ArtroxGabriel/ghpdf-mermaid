"""Mermaid diagram extension for Python-Markdown."""

import base64
import html
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

MERMAID_INK_SVG_URL = "https://mermaid.ink/svg/{}"
MERMAID_TIMEOUT = 15
MERMAID_USER_AGENT = "ghpdf/1.0 (+https://github.com/ArtroxGabriel/ghpdf-mermaid)"
MERMAID_OFFLINE_ENV = "GHPDF_MERMAID_OFFLINE"


def _wrap_mermaid_svg(raw: str) -> str | None:
    """Extract SVG tag and wrap in container div."""
    idx = raw.find("<svg")
    return f'<div class="mermaid">{raw[idx:].strip()}</div>' if idx != -1 else None


def _render_mermaid_local(code: str) -> str | None:
    """Render Mermaid code to SVG using local mmdc. None on failure or missing binary."""
    mmdc = shutil.which("mmdc")
    if not mmdc:
        return None

    # Disable htmlLabels so labels render as standard SVG <text> elements
    # rather than HTML <foreignObject> which WeasyPrint cannot render.
    mermaid_cfg = {
        "htmlLabels": False,
        "flowchart": {"htmlLabels": False},
        "sequence": {"useMaxWidth": True},
    }
    puppeteer_cfg = {"args": ["--no-sandbox", "--disable-setuid-sandbox"]}

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        m_path = tmp_path / "mermaid.json"
        p_path = tmp_path / "puppeteer.json"
        m_path.write_text(json.dumps(mermaid_cfg))
        p_path.write_text(json.dumps(puppeteer_cfg))

        try:
            proc = subprocess.run(
                [mmdc, "-i", "-", "-o", "-", "-c", str(m_path), "-p", str(p_path)],
                input=code,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            if proc.returncode == 0:
                return _wrap_mermaid_svg(proc.stdout)
        except (subprocess.SubprocessError, OSError):
            pass

    return None


def _render_mermaid_remote(code: str) -> str | None:
    """Render Mermaid code to SVG via mermaid.ink. None on failure."""
    # Prepend directive to disable htmlLabels so mermaid.ink returns pure SVG <text> tags
    # instead of <foreignObject>, ensuring full compatibility with WeasyPrint vectors.
    init_directive = '%%{init: {"flowchart": {"htmlLabels": false}, "htmlLabels": false}}%%\n'
    diagram_source = init_directive + code if "%%{init:" not in code else code

    encoded = base64.urlsafe_b64encode(diagram_source.encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        MERMAID_INK_SVG_URL.format(encoded),
        headers={"User-Agent": MERMAID_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=MERMAID_TIMEOUT) as resp:
            if resp.status == 200:
                return _wrap_mermaid_svg(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError):
        pass

    return None


def render_mermaid(code: str, allow_remote: bool = True) -> str:
    """Render Mermaid code block to SVG (local mmdc or remote mermaid.ink fallback)."""
    source = code.strip()
    if not source:
        return ""

    # 1. Local attempt via mmdc (SVG)
    rendered = _render_mermaid_local(source)
    if rendered:
        return rendered

    # 2. Remote attempt via mermaid.ink (SVG) unless offline mode is enabled
    is_offline = not allow_remote or os.environ.get(MERMAID_OFFLINE_ENV) == "1"
    if not is_offline:
        rendered = _render_mermaid_remote(source)
        if rendered:
            return rendered

    # 3. Fallback to raw code block
    escaped_code = html.escape(code)
    return f'<pre><code class="language-mermaid">{escaped_code}</code></pre>'


class MermaidPreprocessor(Preprocessor):
    """Preprocessor to extract ```mermaid blocks and replace with rendered HTML."""

    def __init__(self, md=None, allow_remote: bool = True):
        super().__init__(md)
        self.allow_remote = allow_remote

    def run(self, lines: list[str]) -> list[str]:
        new_lines: list[str] = []
        in_mermaid = False
        block_lines: list[str] = []

        def flush_block() -> None:
            rendered = render_mermaid("\n".join(block_lines), allow_remote=self.allow_remote)
            new_lines.extend(rendered.splitlines())

        for line in lines:
            stripped = line.strip()
            if not in_mermaid:
                if stripped == "```mermaid" or stripped.startswith("```mermaid "):
                    in_mermaid = True
                    block_lines = []
                else:
                    new_lines.append(line)
            elif stripped == "```":
                in_mermaid = False
                flush_block()
            else:
                block_lines.append(line)

        if in_mermaid:
            flush_block()

        return new_lines


class MermaidExtension(Extension):
    """Markdown extension for Mermaid diagrams."""

    def __init__(self, **kwargs):
        self.config = {
            "allow_remote": [True, "Allow remote rendering fallback via mermaid.ink"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        allow_remote = self.getConfig("allow_remote")
        md.preprocessors.register(MermaidPreprocessor(md, allow_remote=allow_remote), "mermaid", 35)


def makeExtension(**kwargs):
    return MermaidExtension(**kwargs)
