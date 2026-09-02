"""Core conversion functions for ghpdf."""

import io
import re
from pathlib import Path

import markdown
from weasyprint import HTML

from ghpdf.mermaid import MermaidExtension

STATIC_DIR = Path(__file__).parent / "static"
GITHUB_CSS_PATH = STATIC_DIR / "github.css"

# Page break marker pattern - matches various formats
PAGE_BREAK_PATTERN = re.compile(
    r"^(?:---\s*pagebreak\s*---|<!--\s*pagebreak\s*-->|\\pagebreak)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
PAGE_BREAK_HTML = '<div class="pagebreak"></div>'

# GitHub-styled vector SVG checkboxes for task lists
CHECKBOX_UNCHECKED = (
    '<span class="task-list-item-checkbox">'
    '<svg viewBox="0 0 16 16">'
    '<rect x="1" y="1" width="14" height="14" rx="3" fill="#ffffff" stroke="#d1d9e0" stroke-width="1.5"/>'
    '</svg></span>'
)
CHECKBOX_CHECKED = (
    '<span class="task-list-item-checkbox">'
    '<svg viewBox="0 0 16 16">'
    '<rect width="16" height="16" rx="3" fill="#1f883d" stroke="#1f883d" stroke-width="1.5"/>'
    '<path d="M3.5 8.5L6.5 11.5L12.5 4.5" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg></span>'
)

# CSS for page numbers
PAGE_NUMBERS_CSS = """
@page {
    @bottom-center {
        content: counter(page);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        font-size: 11px;
        color: #656d76;
    }
}
"""


def get_github_css() -> str:
    """Load GitHub-style CSS."""
    return GITHUB_CSS_PATH.read_text()


def preprocess_pagebreaks(md_content: str) -> str:
    """Convert page break markers to HTML."""
    return PAGE_BREAK_PATTERN.sub(PAGE_BREAK_HTML, md_content)


def preprocess_html_blocks(md_content: str) -> str:
    """Enable markdown parsing inside <details> blocks for md_in_html extension."""
    def add_md_attr(m: re.Match) -> str:
        attrs = m.group(1)
        if "markdown=" in attrs:
            return m.group(0)
        return f'<details markdown="1"{attrs}>'

    content = re.sub(r"<details(\s*[^>]*)>", add_md_attr, md_content, flags=re.IGNORECASE)
    # Ensure empty line after </summary> so markdown processor recognizes inner content
    return re.sub(r"(</summary>)\s*\n(?!\s*\n)", r"\1\n\n", content, flags=re.IGNORECASE)


def preprocess_task_lists(md_content: str) -> str:
    """Convert GFM task list markers [ ] and [x] into styled vector SVG checkboxes."""
    md_content = re.sub(r"^(\s*[-*+]\s+)\[ \]\s+", r"\1" + CHECKBOX_UNCHECKED + " ", md_content, flags=re.MULTILINE)
    md_content = re.sub(r"^(\s*[-*+]\s+)\[[xX]\]\s+", r"\1" + CHECKBOX_CHECKED + " ", md_content, flags=re.MULTILINE)
    return md_content


def markdown_to_html(md_content: str, mermaid_offline: bool = False) -> str:
    """Convert markdown to HTML with extensions."""
    md_content = preprocess_pagebreaks(md_content)
    md_content = preprocess_html_blocks(md_content)
    md_content = preprocess_task_lists(md_content)

    extensions = [
        "markdown.extensions.fenced_code",
        "markdown.extensions.codehilite",
        "markdown.extensions.tables",
        "markdown.extensions.toc",
        "markdown.extensions.nl2br",
        "markdown.extensions.sane_lists",
        "markdown.extensions.smarty",
        "markdown.extensions.admonition",
        "markdown.extensions.def_list",
        "markdown.extensions.abbr",
        "markdown.extensions.footnotes",
        "markdown.extensions.md_in_html",
        MermaidExtension(allow_remote=not mermaid_offline),
    ]

    extension_configs = {
        "markdown.extensions.codehilite": {
            "css_class": "highlight",
            "guess_lang": True,
            "linenums": False,
        },
        "markdown.extensions.toc": {
            "permalink": False,
        },
    }

    md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
    return md.convert(md_content)


def create_html_document(body: str, css: str, page_numbers: bool = False) -> str:
    """Create a complete HTML document with styling."""
    extra_css = PAGE_NUMBERS_CSS if page_numbers else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
{css}
{extra_css}
    </style>
</head>
<body>
{body}
</body>
</html>"""


def html_to_pdf(html_content: str) -> bytes:
    """Convert HTML to PDF using WeasyPrint."""
    html = HTML(string=html_content)
    pdf_buffer = io.BytesIO()
    html.write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()


def convert(
    content: str,
    page_numbers: bool = False,
    mermaid_offline: bool = False,
) -> bytes:
    """Convert markdown content to PDF bytes.

    Args:
        content: Markdown text to convert
        page_numbers: Add page numbers at bottom center
        mermaid_offline: Disable network fallback (mermaid.ink) for Mermaid diagrams

    Returns:
        PDF file as bytes
    """
    css = get_github_css()
    html_body = markdown_to_html(content, mermaid_offline=mermaid_offline)
    html_document = create_html_document(html_body, css, page_numbers=page_numbers)
    return html_to_pdf(html_document)
