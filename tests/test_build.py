"""
Tests for "se build" command.
"""

from pathlib import Path
from helpers import must_run, assemble_book

def test_build_clean(draft_dir: Path, work_dir: Path, data_dir: Path, book_name: str):
	"""Run the build command on a known-clean book and verify that
	the correct number and type of output files are generated.
	"""
	text_dir = data_dir / "build" / "text"
	book_dir = assemble_book(draft_dir, work_dir, text_dir)
	must_run(f"se build --kindle --kobo --check {book_dir}")

	for suffix in [".epub", "_advanced.epub", ".azw3", ".kepub.epub"]:
		file = work_dir / (book_name + suffix)
		assert file.is_file()
