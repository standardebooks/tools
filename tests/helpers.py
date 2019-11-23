"""
Common helper functions for tests.
"""

import subprocess
import shlex
import shutil
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
