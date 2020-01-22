"""
Common helper functions for tests.
"""

import filecmp
import shlex
import shutil
import subprocess
from pathlib import Path
import pytest


def run(cmd: str) -> subprocess.CompletedProcess:
	"""Run the provided shell string as a command in a subprocess. Returns a
	status object when the command completes.
	"""
	args = shlex.split(cmd)
	return subprocess.run(args, stderr=subprocess.PIPE, check=False)

def must_run(cmd: str) -> None:
	"""Run the provided shell string as a command in a subprocess. Forces a
	test failure if the command fails.
	"""
	result = run(cmd)
	if result.returncode == 0:
		if not result.stderr:
			return
		pytest.fail("stderr was not empty after command '{}'\n{}".format(cmd, result.stderr.decode()))
	else:
		fail_msg = "error code {} from command '{}'".format(result.returncode, cmd)
		if result.stderr:
			fail_msg += "\n" + result.stderr.decode()
		pytest.fail(fail_msg)

def assemble_book(draft__dir: Path, work_dir: Path, text_dir: Path) -> Path:
	"""Merge contents of draft book skeleton with test-specific files for
	the book contents.
	"""
	book_dir = work_dir / "test-book"
	# Copy skeleton from draft__dir
	shutil.copytree(draft__dir, book_dir)
	# Add metadata and text files for test book
	if (text_dir / "content.opf").is_file():
		shutil.copy(text_dir / "content.opf", book_dir / "src" / "epub")
	for file in text_dir.glob("*.xhtml"):
		shutil.copy(file, book_dir / "src" / "epub" / "text")
	# Rebuild file metadata
	must_run("se print-manifest-and-spine --in-place {}".format(book_dir))
	must_run("se print-toc --in-place {}".format(book_dir))
	return book_dir

def files_are_golden(in_dir: Path, text_dir: Path, golden_dir: Path, update_golden: bool) -> bool:
	"""Check that the files in the list have identical contents in both
	directories."""
	# Get the list of files to check
	files = [file.name for file in list(in_dir.glob("*.xhtml"))]
	assert files

	# If we want to replace the golden files, copy them before checking.
	# The checking should always succeed after copying.
	if update_golden:
		for file_to_update in files:
			shutil.copy(text_dir / file_to_update, golden_dir)

	# Check all files
	_, mismatches, errors = filecmp.cmpfiles(str(golden_dir), str(text_dir), files)
	# If there are mismatches, do an assert on the text of the files
	# so that we get a nice context diff from pytest.
	for mismatch in mismatches:
		with open(golden_dir / mismatch) as file:
			golden_text = file.read()
		with open(text_dir / mismatch) as file:
			test_text = file.read()
		assert golden_text == test_text

	# Do a redundant check in case there is no text diff for some reason
	assert mismatches == []
	# Fail on any other errors
	assert errors == []

	return True
