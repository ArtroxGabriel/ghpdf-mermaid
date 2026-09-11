"""CLI interface for ghpdf using Typer."""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from ghpdf import __version__
from ghpdf.converter import convert

app = typer.Typer(
    name="ghpdf",
    help="Convert Markdown files to PDF with GitHub-style rendering and Mermaid support.",
    add_completion=False,
    no_args_is_help=False,
)

console = Console(stderr=True)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"ghpdf {__version__}")
        raise typer.Exit()


def derive_output_path(input_path: Path) -> Path:
    """Convert input.md to input.pdf in the same directory."""
    return input_path.with_suffix(".pdf")


def is_stdin_available() -> bool:
    """Check if data is available on stdin."""
    return not sys.stdin.isatty()


def convert_file(
    input_path: Path,
    output_path: Path,
    page_numbers: bool,
    quiet: bool,
    mermaid_offline: bool = False,
) -> bool:
    """Convert a single file. Returns True on success."""
    try:
        md_content = input_path.read_text(encoding="utf-8")
        pdf_bytes = convert(md_content, page_numbers, mermaid_offline=mermaid_offline)
        output_path.write_bytes(pdf_bytes)

        if not quiet:
            console.print(f"[green]Created:[/green] {output_path}")

        return True

    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {input_path}")
        return False
    except PermissionError:
        console.print(f"[red]Error:[/red] Permission denied: {output_path}")
        return False
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to convert {input_path}: {e}")
        return False


@app.command()
def main(
    files: Annotated[
        Optional[list[Path]],
        typer.Argument(
            help="Markdown files to convert. Reads from stdin if not provided.",
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "-o",
            "--output",
            help="Output filename (single file or stdin only).",
        ),
    ] = None,
    remote_name: Annotated[
        bool,
        typer.Option(
            "-O",
            "--remote-name",
            help="Use input filename for output (input.md -> input.pdf).",
        ),
    ] = False,
    page_numbers: Annotated[
        bool,
        typer.Option(
            "-n",
            "--page-numbers",
            help="Add page numbers at bottom center.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q",
            "--quiet",
            help="Suppress progress output.",
        ),
    ] = False,
    mermaid_offline: Annotated[
        bool,
        typer.Option(
            "--mermaid-offline",
            help="Disable remote network fallback (mermaid.ink) for Mermaid diagrams.",
        ),
    ] = False,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "-V",
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Convert Markdown to PDF with GitHub-style rendering and Mermaid diagram support.
    
    Mermaid diagrams (```mermaid ... ``` blocks) are automatically detected and
    rendered to SVG vector graphics when `mermaid-cli` (mmdc) or npx is available.

    Examples:

        ghpdf README.md -o docs.pdf      Single file, explicit output

        ghpdf README.md -O               Auto-name: README.pdf

        ghpdf *.md -O                    Bulk convert all .md files

        cat doc.md | ghpdf > out.pdf     Stdin to stdout

        cat doc.md | ghpdf -o out.pdf    Stdin to file
    """
    input_files = files or []

    # Validate conflicting options
    if remote_name and output:
        console.print("[red]Error:[/red] Cannot use both -O and -o together.")
        raise typer.Exit(code=1)

    if len(input_files) > 1 and output:
        console.print(
            "[red]Error:[/red] Cannot use -o with multiple input files. Use -O instead."
        )
        raise typer.Exit(code=1)

    # No files provided - check for stdin
    if not input_files:
        if not is_stdin_available():
            console.print(
                "[red]Error:[/red] No input files provided and no data on stdin."
            )
            console.print("Run 'ghpdf --help' for usage information.")
            raise typer.Exit(code=1)

        if remote_name:
            console.print(
                "[red]Error:[/red] Cannot use -O with stdin (no filename to derive)."
            )
            raise typer.Exit(code=1)

        md_content = sys.stdin.read()

        if not md_content.strip():
            console.print("[red]Error:[/red] Empty input received.")
            raise typer.Exit(code=1)

        try:
            pdf_bytes = convert(md_content, page_numbers, mermaid_offline=mermaid_offline)
        except Exception as e:
            console.print(f"[red]Error:[/red] Conversion failed: {e}")
            raise typer.Exit(code=1)

        if output:
            output.write_bytes(pdf_bytes)
            if not quiet:
                console.print(f"[green]Created:[/green] {output}")
        else:
            sys.stdout.buffer.write(pdf_bytes)

        raise typer.Exit(code=0)

    # Validate all files exist first
    missing_files = [f for f in input_files if not f.exists()]
    if missing_files:
        for f in missing_files:
            console.print(f"[red]Error:[/red] File not found: {f}")
        raise typer.Exit(code=1)

    # Validate output options
    if not output and not remote_name:
        error_msg = (
            "No output specified. Use -o <file> or -O."
            if len(input_files) == 1
            else "Multiple files require -O flag for auto-naming."
        )
        console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(code=1)

    # Process conversions
    jobs = [(input_files[0], output)] if output else [(f, derive_output_path(f)) for f in input_files]
    success_count = sum(
        convert_file(src, dst, page_numbers, quiet, mermaid_offline=mermaid_offline)
        for src, dst in jobs
    )
    fail_count = len(jobs) - success_count

    if not quiet and len(jobs) > 1:
        if fail_count == 0:
            console.print(f"[green]Converted {success_count} file(s) successfully.[/green]")
        else:
            console.print(
                f"[yellow]Converted {success_count} file(s), {fail_count} failed.[/yellow]"
            )

    raise typer.Exit(code=1 if fail_count > 0 else 0)


if __name__ == "__main__":
    app()
