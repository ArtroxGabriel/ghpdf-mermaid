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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as m_file, \
         tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as p_file:
        json.dump(mermaid_cfg, m_file)
        json.dump(puppeteer_cfg, p_file)
        m_path = m_file.name
        p_path = p_file.name

    try:
        proc = subprocess.run(
            [mmdc, "-i", "-", "-o", "-", "-c", m_path, "-p", p_path],
            input=code,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if proc.returncode == 0 and "<svg" in proc.stdout:
            svg_content = proc.stdout[proc.stdout.find("<svg"):]
            return f'<div class="mermaid">{svg_content.strip()}</div>'
    except (subprocess.SubprocessError, OSError):
        pass
    finally:
        for path in (m_path, p_path):
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
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
                svg_content = resp.read().decode("utf-8")
                if "<svg" in svg_content:
                    svg_content = svg_content[svg_content.find("<svg"):]
                    return f'<div class="mermaid">{svg_content.strip()}</div>'
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

        for line in lines:
            stripped = line.strip()
            if not in_mermaid:
                if stripped == "```mermaid" or stripped.startswith("```mermaid "):
                    in_mermaid = True
                    block_lines = []
                else:
                    new_lines.append(line)
            else:
                if stripped == "```":
                    in_mermaid = False
                    rendered = render_mermaid("\n".join(block_lines), allow_remote=self.allow_remote)
                    new_lines.extend(rendered.splitlines())
                else:
                    block_lines.append(line)

        # Handle unclosed block gracefully
        if in_mermaid:
            rendered = render_mermaid("\n".join(block_lines), allow_remote=self.allow_remote)
            new_lines.extend(rendered.splitlines())

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
