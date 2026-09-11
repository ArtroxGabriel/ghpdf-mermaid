"""Tests for general markdown and PDF conversion functions in ghpdf.converter."""

from ghpdf.converter import (
    convert,
    create_html_document,
    get_github_css,
    html_to_pdf,
    markdown_to_html,
    preprocess_html_blocks,
    preprocess_indented_code_blocks,
    preprocess_lists,
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


def test_preprocess_lists_directly_following_paragraph():
    """Ensure bullet lists starting with - or * directly after paragraphs become lists."""
    md_content = """Paragraph:
- item 1
- item 2
* item 3"""
    html_out = markdown_to_html(md_content)
    assert "<ul>" in html_out
    assert "<li>item 1</li>" in html_out
    assert "<li>item 2</li>" in html_out
    assert "<li>item 3</li>" in html_out
    assert "- item 1" not in html_out


def test_preprocess_indented_code_blocks_in_lists():
    """Verify indented code block fences are transformed into native indented code blocks."""
    # Arrange
    md_content = """* list item

    ```go
        var k = 10
    ```"""

    # Act
    preprocessed = preprocess_indented_code_blocks(md_content)

    # Assert
    assert ":::go" in preprocessed
    assert "```" not in preprocessed


def test_indented_fenced_code_block_renders_highlighted_inside_list():
    """Ensure indented fenced code blocks in lists render as syntax-highlighted blocks."""
    # Arrange
    md_content = """sem identacao a conversao para pdf funciona sem

```go
var k = 10
```

* ja no cenario identado, onde funcionaria bem num visualizador de markdown, a conversao para pdf nao funciona, fica quebrada

    ```go
        var k = 10
    ```"""

    # Act
    html_out = markdown_to_html(md_content)

    # Assert
    # Both the unindented and indented blocks should have highlighted pre/code blocks
    assert html_out.count('class="highlight"') == 2
    assert "<li>" in html_out
    assert "<code>go" not in html_out
