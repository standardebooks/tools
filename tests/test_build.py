"""
Tests for "se build" command.
"""

import shutil
from pathlib import Path
from helpers import must_run

def assemble_book(book_dir: Path, work_dir: Path, data_dir: Path) -> Path:
	"""Merge contents of draft book skeleton with test-specific files for
	the book contents.
	"""
	build_dir = work_dir / "book-to-build"
	# Copy skeleton from book_dir
	shutil.copytree(book_dir, build_dir)
	# Add text files for build tests
	for file in (data_dir / "build" / "text").glob("*.xhtml"):
		shutil.copy(file, build_dir / "src" / "epub" / "text")
	# Rebuild file metadata
	must_run("se print-manifest-and-spine --in-place {}".format(build_dir))
	must_run("se print-toc --in-place {}".format(build_dir))
	return build_dir

def test_build_clean(book_dir: Path, work_dir: Path, data_dir: Path, book_name: str):
	"""Run the build command on a known-clean book and verify that
	the correct number and type of output files are generated.
	"""
	build_dir = assemble_book(book_dir, work_dir, data_dir)
	must_run("se build --kindle --kobo --check {}".format(build_dir))

	for suffix in ["epub", "epub3", "azw3", "kepub.epub"]:
		file = work_dir / (book_name + "." + suffix)
		assert file.is_file()
