"""Tests for the ghpdf CLI interface."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ghpdf.cli import app, derive_output_path, is_stdin_available

runner = CliRunner()


def test_derive_output_path():
    assert derive_output_path(Path("docs/readme.md")) == Path("docs/readme.pdf")
    assert derive_output_path(Path("file.txt")) == Path("file.pdf")


def test_is_stdin_available(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert is_stdin_available() is True

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    assert is_stdin_available() is False


def test_version_flag():
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0
    assert "ghpdf" in result.stdout


def test_help_flag():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Mermaid" in result.stdout
    assert "--mermaid-offline" in result.stdout


def test_conflicting_options():
    result = runner.invoke(app, ["file1.md", "-o", "out.pdf", "-O"])
    assert result.exit_code == 1
    assert "Cannot use both -O and -o together" in result.stderr


def test_multiple_files_with_explicit_output():
    result = runner.invoke(app, ["f1.md", "f2.md", "-o", "out.pdf"])
    assert result.exit_code == 1
    assert "Cannot use -o with multiple input files" in result.stderr


def test_no_files_no_stdin(monkeypatch):
    monkeypatch.setattr("ghpdf.cli.is_stdin_available", lambda: False)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "No input files provided" in result.stderr


def test_missing_input_file(tmp_path):
    missing = tmp_path / "nonexistent.md"
    result = runner.invoke(app, [str(missing), "-O"])
    assert result.exit_code == 1
    assert "File not found" in result.stderr


def test_single_file_no_output_specified(tmp_path):
    doc = tmp_path / "test.md"
    doc.write_text("# Hello")
    result = runner.invoke(app, [str(doc)])
    assert result.exit_code == 1
    assert "No output specified" in result.stderr


def test_single_file_explicit_output(tmp_path):
    doc = tmp_path / "test.md"
    doc.write_text("# Test")
    out = tmp_path / "custom.pdf"

    with patch("ghpdf.cli.convert", return_value=b"%PDF-1.7 mock"):
        result = runner.invoke(app, [str(doc), "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert out.read_bytes() == b"%PDF-1.7 mock"


def test_single_file_remote_name(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Test")
    expected_out = tmp_path / "doc.pdf"

    with patch("ghpdf.cli.convert", return_value=b"%PDF-1.7 mock"):
        result = runner.invoke(app, [str(doc), "-O"])
        assert result.exit_code == 0
        assert expected_out.exists()


def test_multiple_files_bulk_conversion(tmp_path):
    doc1 = tmp_path / "d1.md"
    doc2 = tmp_path / "d2.md"
    doc1.write_text("# Doc 1")
    doc2.write_text("# Doc 2")

    with patch("ghpdf.cli.convert", return_value=b"%PDF-1.7 mock"):
        result = runner.invoke(app, [str(doc1), str(doc2), "-O", "-q"])
        assert result.exit_code == 0
        assert (tmp_path / "d1.pdf").exists()
        assert (tmp_path / "d2.pdf").exists()


def test_multiple_files_without_remote_name(tmp_path):
    doc1 = tmp_path / "d1.md"
    doc2 = tmp_path / "d2.md"
    doc1.write_text("# Doc 1")
    doc2.write_text("# Doc 2")

    result = runner.invoke(app, [str(doc1), str(doc2)])
    assert result.exit_code == 1
    assert "Multiple files require -O flag" in result.stderr


def test_stdin_to_file(tmp_path, monkeypatch):
    monkeypatch.setattr("ghpdf.cli.is_stdin_available", lambda: True)
    out = tmp_path / "stdin_out.pdf"

    with patch("ghpdf.cli.convert", return_value=b"%PDF-1.7 mock"):
        result = runner.invoke(app, ["-o", str(out)], input="# Stdin text")
        assert result.exit_code == 0
        assert out.exists()
        assert out.read_bytes() == b"%PDF-1.7 mock"


def test_stdin_with_remote_name(monkeypatch):
    monkeypatch.setattr("ghpdf.cli.is_stdin_available", lambda: True)
    result = runner.invoke(app, ["-O"], input="# Test")
    assert result.exit_code == 1
    assert "Cannot use -O with stdin" in result.stderr


def test_stdin_empty(monkeypatch):
    monkeypatch.setattr("ghpdf.cli.is_stdin_available", lambda: True)
    result = runner.invoke(app, ["-o", "out.pdf"], input="   \n")
    assert result.exit_code == 1
    assert "Empty input received" in result.stderr
