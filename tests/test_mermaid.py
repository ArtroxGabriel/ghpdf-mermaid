"""Tests for Mermaid diagram extension and rendering."""

import os
import shutil
import subprocess
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from ghpdf.converter import convert, markdown_to_html
from ghpdf.mermaid import MermaidExtension, render_mermaid


def test_render_mermaid_local_success(monkeypatch):
    """Ensure local mmdc executes and returns SVG output."""
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/mmdc" if cmd == "mmdc" else None)

    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "<svg><g><text>Diagram</text></g></svg>"
    mock_run.stderr = ""

    with patch("subprocess.run", return_value=mock_run) as mock_sub:
        svg = render_mermaid("graph TD; A-->B;")
        assert svg == '<div class="mermaid"><svg><g><text>Diagram</text></g></svg></div>'
        assert mock_sub.called
        args, kwargs = mock_sub.call_args
        assert args[0][0] == "/usr/bin/mmdc"
        assert kwargs["input"] == "graph TD; A-->B;"


def test_render_mermaid_remote_fallback(monkeypatch):
    """When mmdc is missing, falls back to mermaid.ink SVG."""
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    monkeypatch.delenv("GHPDF_MERMAID_OFFLINE", raising=False)

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.read.return_value = b"<svg><g><text>Remote Diagram</text></g></svg>"
    fake_resp.__enter__.return_value = fake_resp

    with patch("urllib.request.urlopen", return_value=fake_resp):
        html_out = render_mermaid("graph TD; A-->B;")
        assert '<div class="mermaid"><svg><g><text>Remote Diagram</text></g></svg></div>' in html_out


def test_render_mermaid_offline_fallback(monkeypatch):
    """When mmdc is missing and offline mode is set, falls back to raw code block."""
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    monkeypatch.setenv("GHPDF_MERMAID_OFFLINE", "1")

    html_out = render_mermaid("graph TD;\n  A --> B;")
    assert '<pre><code class="language-mermaid">' in html_out
    assert "graph TD;\n  A --&gt; B;</code></pre>" in html_out


def test_render_mermaid_allow_remote_false(monkeypatch):
    """When allow_remote=False, skips network call and falls back to code block."""
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    monkeypatch.delenv("GHPDF_MERMAID_OFFLINE", raising=False)

    html_out = render_mermaid("graph TD;\n  A --> B;", allow_remote=False)
    assert '<pre><code class="language-mermaid">' in html_out


def test_render_mermaid_error_fallback(monkeypatch):
    """Fallback to code block when local and remote both fail."""
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/mmdc" if cmd == "mmdc" else None)
    monkeypatch.setenv("GHPDF_MERMAID_OFFLINE", "1")

    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stdout = ""
    mock_run.stderr = "Parse error on line 1"

    with patch("subprocess.run", return_value=mock_run):
        code = "invalid mermaid syntax"
        output = render_mermaid(code)
        assert '<pre><code class="language-mermaid">' in output
        assert "invalid mermaid syntax" in output


def test_markdown_to_html_with_mermaid(monkeypatch):
    """Verify markdown containing mermaid code fence is replaced."""
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/mmdc" if cmd == "mmdc" else None)

    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "<svg>mock</svg>"
    mock_run.stderr = ""

    md_content = """# Hello

```mermaid
graph LR
    A --> B
```

Footer text.
"""
    with patch("subprocess.run", return_value=mock_run):
        html_out = markdown_to_html(md_content)
        assert '<div class="mermaid"><svg>mock</svg></div>' in html_out
        assert "Hello</h1>" in html_out
        assert "<p>Footer text.</p>" in html_out


def test_markdown_to_html_without_mermaid():
    """Verify standard markdown with non-mermaid code block unaffected."""
    md_content = """```python
print("hello")
```"""
    html_out = markdown_to_html(md_content)
    assert '<div class="mermaid">' not in html_out
    assert 'class="highlight"' in html_out


def test_unclosed_mermaid_block(monkeypatch):
    """Verify unclosed mermaid fence handled without crashing."""
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/mmdc" if cmd == "mmdc" else None)

    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "<svg>unclosed</svg>"
    mock_run.stderr = ""

    md_content = "```mermaid\ngraph TD\n  A --> B"
    with patch("subprocess.run", return_value=mock_run):
        html_out = markdown_to_html(md_content)
        assert '<div class="mermaid"><svg>unclosed</svg></div>' in html_out


def test_make_extension():
    from ghpdf.mermaid import makeExtension
    ext = makeExtension()
    assert isinstance(ext, MermaidExtension)


def test_convert_pdf_with_mermaid(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/mmdc" if cmd == "mmdc" else None)
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'
    mock_run.stderr = ""

    with patch("subprocess.run", return_value=mock_run):
        pdf_bytes = convert("# Test\n\n```mermaid\ngraph LR\nA-->B\n```")
        assert pdf_bytes.startswith(b"%PDF")


def test_markdown_inside_details_block():
    """Verify bold, code blocks, etc. inside <details> tags render as HTML."""
    md_content = """<details>
<summary><strong>Prerequisites</strong></summary>

**macOS** (Homebrew):

```bash
brew install pango
```
</details>"""
    html_out = markdown_to_html(md_content)
    assert "<strong>macOS</strong>" in html_out
    assert "class=\"highlight\"" in html_out or "<code" in html_out
    assert "**macOS**" not in html_out
