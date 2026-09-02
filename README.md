# ghpdf-mermaid

A CLI tool to convert Markdown files to PDF with GitHub-style rendering and native Mermaid diagram support.

> **Note**: This is a fork of [atlekbai/ghpdf](https://github.com/atlekbai/md2pdf) adding support for [Mermaid](https://mermaid.js.org/) diagram rendering into vector SVG.

## Why

| Feature             | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| **GitHub styling**  | PDFs look exactly like GitHub renders Markdown               |
| **Mermaid support** | Seamlessly renders ````mermaid` blocks into sharp vector PDF diagrams |
| **Simple**          | No LaTeX, no complex templates                               |
| **Curl-like flags** | Familiar `-o` and `-O` flags for output control              |
| **Wildcards**       | Bulk convert with `ghpdf *.md -O`                            |

<img src="https://github.com/user-attachments/assets/94126b34-0ef5-4f1c-8e69-de8e4d22f3ce" alt="Sample PDF output" width="400">

## Installation

<details>
<summary><strong>Prerequisites</strong> (system libraries required by WeasyPrint)</summary>

**macOS** (Homebrew):

```bash
brew install pango
```

**Ubuntu/Debian**:

```bash
sudo apt install libpango-1.0-0 libpangocairo-1.0-0
```

**Fedora**:

```bash
sudo dnf install pango
```

**Windows**: See [WeasyPrint Windows installation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows)

</details>

### Arch Linux (AUR)

```bash
yay -S ghpdf-mermaid
# or
paru -S ghpdf-mermaid
```

### Install with uv / pipx

```bash
uv tool install git+https://github.com/ArtroxGabriel/ghpdf-mermaid.git
# or
pipx install git+https://github.com/ArtroxGabriel/ghpdf-mermaid.git
```

### Mermaid Diagram Requirements

To render Mermaid diagrams (` ```mermaid ... ``` `) into vector SVG inside your PDFs:

- **Arch Linux**: `sudo pacman -S mermaid-cli` (or via AUR: `yay -S mermaid-cli`)
- **Node.js / npm**: `npm install -g @mermaid-js/mermaid-cli`
- **Fallback**: If `mmdc` is not installed globally, `ghpdf` will automatically attempt running it through `npx` if Node is installed. If neither is available or if diagram syntax fails, it gracefully falls back to displaying the raw code block.



## Quick Start

```bash
# Convert a file
ghpdf README.md -o output.pdf

# Auto-name output (README.md → README.pdf)
ghpdf README.md -O
```

## Usage

```bash
ghpdf [OPTIONS] [FILES]...
```

### Options

| Flag | Long             | Description                                 |
| ---- | ---------------- | ------------------------------------------- |
| `-o` | `--output`       | Output filename (single file or stdin only) |
| `-O` | `--remote-name`  | Auto-name output (input.md → input.pdf)     |
| `-n` | `--page-numbers` | Add page numbers at bottom center           |
| `-q` | `--quiet`        | Suppress progress output                    |
| `-V` | `--version`      | Show version and exit                       |

### Examples

```bash
# Single file with explicit output
ghpdf README.md -o documentation.pdf

# Auto-name output (README.md → README.pdf)
ghpdf README.md -O

# Bulk convert all markdown files
ghpdf *.md -O

# With page numbers
ghpdf report.md -O -n

# Stdin to file
echo "# Hello World" | ghpdf -o hello.pdf

# Stdin to stdout (for piping)
cat document.md | ghpdf > output.pdf

# Quiet mode for scripting
ghpdf *.md -O -q
```

## Features

- GitHub-flavored markdown styling
- Mermaid diagram rendering (via `mermaid-cli` / `mmdc`)
- Syntax highlighting for code blocks
- Tables, task lists, footnotes, and more
- Page break support
- Optional page numbers
- Bulk conversion
- Stdin/stdout piping

### Supported Markdown

Headings, bold, italic, strikethrough, lists, task lists, code blocks, inline code, tables, blockquotes, horizontal rules, links, images, footnotes, definition lists, abbreviations, admonitions, and Mermaid diagrams (````mermaid`).

### Page Breaks

Insert page breaks using any of these formats:

```
---pagebreak---
<!-- pagebreak -->
\pagebreak
```

## Credits & Acknowledgments

This project is a fork of [`ghpdf`](https://github.com/atlekbai/md2pdf) originally created by [@atlekbai](https://github.com/atlekbai), extended with Mermaid diagram parsing and vector rendering.

## License

MIT
