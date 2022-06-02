"""
Tests for commands the cleanup or transform the epub text.
"""

from pathlib import Path
import pytest
from helpers import assemble_book, must_run, files_are_golden

TEXT_CMDS = [
    ("british2american", ""),
    ("clean", ""),
    ("modernize-spelling", ""),
    ("semanticate", ""),
    ("typogrify", ""),
    ("build-manifest", ""),
    ("build-spine", ""),
]

@pytest.mark.parametrize("cmd_name, cmd_args", TEXT_CMDS)
def test_text_cmds(data_dir: Path, draft_dir: Path, work_dir: Path, cmd_name: str, cmd_args: str, update_golden: bool):
	"""Run each command on the input content and validate that the
	transformed text matches the expected output content."""
	in_dir = data_dir / cmd_name / "in"
	book_dir = assemble_book(draft_dir, work_dir, in_dir)

	must_run(f"se {cmd_name} {cmd_args} {book_dir}")

	text_dir = book_dir / "src" / "epub" / "text"
	golden_dir = data_dir / cmd_name / "out"
	assert files_are_golden(in_dir, text_dir, golden_dir, update_golden)
