"""Tests for general markdown and PDF conversion functions in ghpdf.converter."""

from ghpdf.converter import (
    convert,
    create_html_document,
    get_github_css,
    html_to_pdf,
    markdown_to_html,
    preprocess_html_blocks,
    preprocess_pagebreaks,
    preprocess_task_lists,
)


def test_get_github_css():
    css = get_github_css()
    assert isinstance(css, str)
    assert len(css) > 100
    assert "body" in css


def test_preprocess_pagebreaks():
    content = """Page 1
---pagebreak---
Page 2
<!-- pagebreak -->
Page 3
\\pagebreak
Page 4"""
    result = preprocess_pagebreaks(content)
    assert result.count('<div class="pagebreak"></div>') == 3
    assert "---pagebreak---" not in result
    assert "\\pagebreak" not in result


def test_preprocess_html_blocks():
    content = """<details>
<summary>Summary title</summary>
**Bold item** inside details
</details>"""
    result = preprocess_html_blocks(content)
    assert '<details markdown="1"' in result
    assert "</summary>\n\n" in result


def test_preprocess_task_lists():
    md_content = """
- [ ] Incomplete task
- [x] Completed task
- [X] Another completed task
* [ ] Asterisk task
+ [x] Plus task
"""
    html_out = markdown_to_html(md_content)
    assert '<span class="task-list-item-checkbox"><svg' in html_out
    assert 'fill="#1f883d"' in html_out  # Checked green box
    assert 'fill="#ffffff"' in html_out  # Unchecked white box
    assert "[ ]" not in html_out
    assert "[x]" not in html_out
    assert "[X]" not in html_out


def test_markdown_inside_details_block():
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


def test_create_html_document():
    doc_without_pages = create_html_document("<p>Hello</p>", "body { color: black; }", page_numbers=False)
    assert "<!DOCTYPE html>" in doc_without_pages
    assert "<p>Hello</p>" in doc_without_pages
    assert "@bottom-center" not in doc_without_pages

    doc_with_pages = create_html_document("<p>Hello</p>", "body { color: black; }", page_numbers=True)
    assert "@bottom-center" in doc_with_pages
    assert "counter(page)" in doc_with_pages


def test_html_to_pdf_and_convert():
    pdf_bytes = convert("# Sample Document\n\nParagraph text.", page_numbers=True)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
