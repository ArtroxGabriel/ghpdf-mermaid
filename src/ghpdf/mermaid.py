"""Mermaid diagram extension for Python-Markdown."""

import html
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


def _get_mmdc_cmd() -> list[str] | None:
    """Return mmdc command prefix if installed in PATH."""
    mmdc = shutil.which("mmdc")
    if mmdc:
        return [mmdc]
    return None


def render_mermaid_to_svg(code: str) -> str:
    """Render Mermaid code to SVG using mmdc, fallback to code block on failure."""
    cmd_prefix = _get_mmdc_cmd()
    if not cmd_prefix:
        escaped_code = html.escape(code)
        return f'<pre><code class="language-mermaid">{escaped_code}</code></pre>'

    # Mermaid config: disable htmlLabels so labels render as standard SVG <text>
    # elements instead of <foreignObject>, which WeasyPrint doesn't render.
    mermaid_cfg = {
        "htmlLabels": False,
        "flowchart": {"htmlLabels": False},
        "sequence": {"useMaxWidth": True},
    }

    # Puppeteer args for Linux/container environment compatibility
    puppeteer_cfg = {"args": ["--no-sandbox", "--disable-setuid-sandbox"]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as m_file, \
         tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as p_file:
        json.dump(mermaid_cfg, m_file)
        json.dump(puppeteer_cfg, p_file)
        m_path = m_file.name
        p_path = p_file.name

    try:
        proc = subprocess.run(
            [*cmd_prefix, "-i", "-", "-o", "-", "-c", m_path, "-p", p_path],
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

    escaped_code = html.escape(code)
    return f'<pre><code class="language-mermaid">{escaped_code}</code></pre>'


class MermaidPreprocessor(Preprocessor):
    """Preprocessor to extract ```mermaid blocks and replace with rendered HTML."""

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
                    rendered = render_mermaid_to_svg("\n".join(block_lines))
                    new_lines.extend(rendered.splitlines())
                else:
                    block_lines.append(line)

        # Handle unclosed block gracefully
        if in_mermaid:
            rendered = render_mermaid_to_svg("\n".join(block_lines))
            new_lines.extend(rendered.splitlines())

        return new_lines


class MermaidExtension(Extension):
    """Markdown extension for Mermaid diagrams."""

    def extendMarkdown(self, md):
        md.preprocessors.register(MermaidPreprocessor(md), "mermaid", 35)


def makeExtension(**kwargs):
    return MermaidExtension(**kwargs)
