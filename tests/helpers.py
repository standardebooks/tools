"""
Common helper functions for tests.
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path
import pytest

def run(cmd: str) -> subprocess.CompletedProcess:
	"""
	Run the provided shell string as a command in a subprocess. Returns a
	status object when the command completes.
	"""
	args = shlex.split(cmd)
	return subprocess.run(args, stderr=subprocess.PIPE, check=False)

def must_run(cmd: str) -> None:
	"""
	Run the provided shell string as a command in a subprocess. Forces a
	test failure if the command fails.
	"""
	result = run(cmd)
	if result.returncode == 0:
		if not result.stderr:
			return
		pytest.fail(f"stderr was not empty after command '{cmd}'\n{result.stderr.decode()}")
	else:
		fail_msg = f"error code {result.returncode} from command '{cmd}'"
		if result.stderr:
			fail_msg += "\n" + result.stderr.decode()
		pytest.fail(fail_msg)

# is there a subdirectory in the test data?
def subdir_present(test_dir: Path) -> bool:
	"""
	Determine if the test input directory has a subdirectory in it
	"""
	with os.scandir(test_dir) as entries:
		for entry in entries:
			if entry.is_dir():
				return True
	return False

def assemble_draftbook(draftbook__dir: Path, input_dir: Path, work__dir: Path) -> Path:
	"""
	Merge contents of draft book skeleton with test-specific files for the book contents.

	INPUTS
	draftbook__dir: the directory containing the stock draft ebook files
	input_dir: the directory containing the ebook files specific to this test
	work__dir: the working directory for this test that will contain the combined ebook files
	"""
	book_dir = work__dir / "draftbook"
	# Copy draft book skeleton
	shutil.copytree(draftbook__dir, book_dir)
	# copy the input directory tree over the draft book files
	shutil.copytree(input_dir, book_dir, dirs_exist_ok=True)
	return book_dir

def assemble_testbook(testbook__dir: Path, input_dir: Path, work__dir: Path, build_manifest: bool = True, build_spine: bool = True, build_toc: bool = True) -> Path:
	"""
	Merge contents of complete test book with test-specific files for the book contents.

	INPUTS
	testbook__dir: the directory containing the stock test ebook files
	input_dir: the directory containing the ebook files specific to this test
	work__dir: the working directory for this test that will contain the combined ebook files
	"""
	book_dir = work__dir / "testbook"
	# Copy test book skeleton
	shutil.copytree(testbook__dir, book_dir)
	# copy the input directory over the test book files
	shutil.copytree(input_dir, book_dir, dirs_exist_ok=True)

	# Rebuild file metadata
	if build_manifest:
		must_run(f"se build-manifest {book_dir}")
	if build_spine:
		must_run(f"se build-spine {book_dir}")
	if build_toc:
		must_run(f"se build-toc {book_dir}")
	return book_dir

def files_are_golden(files_dir: Path, results_dir: Path, golden_dir: Path, update_golden: bool) -> bool:
	"""
	Check that the results of the test are the same as the "golden" files.

	INPUTS
	files_dir: the directory containing the file names to be compared
	results_dir: the directory containing the results of the test
	golden_dir: the directory containing the “golden” files, i.e. what the test should produce
	update_golden: Whether to update golden_dir with the files in results_dir before the comparison
	"""
	__tracebackhide__ = True # pylint: disable=unused-variable

	# Get the list of files to check
	files_to_check = []
	files_and_dirs = files_dir.glob("**/*")
	files_to_check = [fd.relative_to(files_dir) for fd in files_and_dirs if fd.is_file()]
	assert files_to_check

	# Either update the golden files from the results…
	if update_golden:
		for file in files_to_check:
			shutil.copy(results_dir / file, golden_dir / file)
	# Or check all the result files against the existing golden files
	else:
		for file in files_to_check:
			with open(golden_dir / file, encoding="utf-8") as gfile:
				golden_text = gfile.read()
			with open(results_dir / file, encoding="utf-8") as rfile:
				result_text = rfile.read()
			assert result_text == golden_text

	return True

def output_is_golden(results: str, golden_file: Path, update_golden: bool) ->bool:
	"""
	Check that out string matches the contents of the golden file.
	"""
	__tracebackhide__ = True # pylint: disable=unused-variable

	if update_golden:
		with open(golden_file, "w", encoding="utf-8") as file:
			file.write(results)

	# Output of stdout should match expected output
	with open(golden_file, encoding="utf-8") as file:
		assert file.read() == results

	return True
