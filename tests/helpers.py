"""
Common helper functions for tests.
"""

import shlex
import shutil
import subprocess
import os
from pathlib import Path
import filecmp
import pytest

def run(cmd: str) -> subprocess.CompletedProcess:
	"""
	Run the provided shell string as a command in a subprocess. Returns a
	status object when the command completes.
	"""
	args = shlex.split(cmd)
	current_environment = os.environ.copy()
	current_environment["COLUMNS"] = "1000000"
	return subprocess.run(args, stderr=subprocess.PIPE, check=False, env=current_environment)

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
	input_dir: the directory containing the ebook files specific to this test; this can be
		non-existent, as git won't save an empty directory, so if there are no input files, then
		the input directory won't exist
	work__dir: the working directory for this test that will contain the combined ebook files
	"""
	book_dir = work__dir / "testbook"
	# Copy test book skeleton
	shutil.copytree(testbook__dir, book_dir)
	# if it exists, copy the input directory over the test book files
	if input_dir.is_dir():
		shutil.copytree(input_dir, book_dir, dirs_exist_ok=True)

	# Rebuild file metadata
	if build_manifest:
		must_run(f"se build-manifest {book_dir}")
	if build_spine:
		must_run(f"se build-spine {book_dir}")
	if build_toc:
		must_run(f"se build-toc {book_dir}")
	return book_dir

def clean_golden_directory(golden_dir: Path) -> None:
	"""
	Delete all files and subdirectory trees in a passed golden directory

	INPUTS
	golden_dir: the golden directory to be cleaned
	"""

	for gfd in golden_dir.glob("*"):
		if gfd.is_file():
			gfd.unlink()
		elif gfd.is_dir():
			shutil.rmtree(gfd)

def get_files(file_dir: Path, file_filter: str = "**/*", excluded_files: list[str] | None = None) -> list[Path]:
	"""
	Return a list of files matching a filter in a given directory.

	INPUTS
	file_dir: The directory to be searched
	file_filter: The glob filter to be used; by default, it searches the entire directory tree
	excluded_files: List of file names to be excluded from the list
	"""

	if excluded_files is None:
		excluded_files = []
	# Always exclude these files
	excluded_files += [".gitignore", ".DS_Store"]
	file_list = []

	file_list = [f.relative_to(file_dir) for f in file_dir.glob(f"{file_filter}") if f.is_file() and f.name not in excluded_files and str(f.parent).find("/.git") == -1]
	return file_list

def build_is_golden(build_dir: Path, extract_dir: Path, golden_dir: Path, update_golden: bool) -> bool:
	"""
	Verify the results of both the build and the extract are the same as the corresponding "golden"
	files.

	INPUTS
	build_dir: the directory containing the build output
	extract_dir: the directory containing the extracted epub files
	golden_dir: the directory containing the “golden” files, i.e. what the test should produce
	update_golden: Whether to update golden_dir with the files in results_dir before the comparison
	"""
	__tracebackhide__ = True # pylint: disable=unused-variable

	golden_build_dir = golden_dir / "build"
	golden_extract_dir = golden_dir / "extract"
	# These files are updated by build from the last commit date. Since this changes after every
	# commit to the tools repository, any future test runs after a commit would fail the comparison
	# tests to the golden files. Therefore exclude them from the compare.
	excluded_extract_files = ["content.opf", "colophon.xhtml"]

	# Get the list of build files (only a single level).
	build_files = []
	build_files = get_files(build_dir, "*")
	assert build_files

	# Get the list of extract files (directory tree)
	extract_files = []
	extract_files = get_files(extract_dir, excluded_files=excluded_extract_files)
	assert extract_files

	# Either update the golden files from the results…
	if update_golden:
		# get rid of everything currently in the golden directory
		clean_golden_directory(golden_dir)

		# copy each file, automatically creating any needed subdirectories in the golden tree
		for file in build_files:
			try:
				shutil.copy(build_dir / file, golden_build_dir / file)
			except FileNotFoundError:
				golden_file_dir = (golden_build_dir / file).parent
				golden_file_dir.mkdir(parents=True, exist_ok=True)
				shutil.copy(build_dir / file, golden_build_dir / file)
				continue

		for file in extract_files:
			try:
				shutil.copy(extract_dir / file, golden_extract_dir / file)
			except FileNotFoundError:
				golden_file_dir = (golden_extract_dir / file).parent
				golden_file_dir.mkdir(parents=True, exist_ok=True)
				shutil.copy(extract_dir / file, golden_extract_dir / file)
				continue

	# … or check all the result files against the existing golden files
	else:
		# Get the list of golden build files (only a single level)
		golden_build_files = get_files(golden_build_dir, "*")
		assert golden_build_files

		# Get the list of golden extract files (directory tree)
		golden_extract_files = get_files(golden_extract_dir, excluded_files=excluded_extract_files)
		assert golden_extract_files

		# get files in build or golden_build but not both
		build_diffs = list(set(build_files).symmetric_difference(golden_build_files))
		for file in build_diffs:
			if file not in build_files:
				assert "" == f"Golden build file {file} not present in test build results"
			else:
				assert "" == f"Extraneous build file {file} not present in golden build files"

		# extract files are checked as normal, i.e. for equality
		extract_same = list(set(extract_files).intersection(golden_extract_files))
		extract_diffs = list(set(extract_files).symmetric_difference(golden_extract_files))

		# files in both are compared for equality
		for file in extract_same:
			# image files aren't utf-8, and a dump isn't useful, so let filecmp handle them
			if file.suffix in (".bmp", ".jpg", ".png", ".tif"):
				if not filecmp.cmp(extract_dir / file, golden_extract_dir / file):
					assert "" == f"Extract image file {file} different than golden file"
			else:
				with open(golden_extract_dir / file, encoding="utf-8") as gfile:
					golden_text = gfile.read()
				with open(extract_dir / file, encoding="utf-8") as rfile:
					extract_text = rfile.read()
				assert extract_text == golden_text

		# files in one but not the other are errors
		for file in extract_diffs:
			if file not in extract_files:
				assert "" == f"Golden extract file {file} not present in test extract results"
			else:
				assert "" == f"Extraneous extract file {file} not present in golden extract files"

	return True

def files_are_golden(command: str, in_dir: Path, results_dir: Path, golden_dir: Path, update_golden: bool) -> bool:
	"""
	Verify the results of a test are the same as the "golden" files.

	INPUTS
	command: the name of the command being tested
	in_dir: the directory containing the input files of the test; this is used to build the list
			of files that will be compared between the results and the golden files
	results_dir: the directory containing the results of the test
	golden_dir: the directory containing the “golden” files, i.e. what the test should produce
	update_golden: Whether to update golden_dir with the files in results_dir before the comparison
	"""
	#__tracebackhide__ = True # pylint: disable=unused-variable

	file_commands = ["create-draft", "extract-ebook", "split-file"]
	result_list_from_results_commands = file_commands + ["build-loi", "shift-illustrations"]
	results_files = []

	if command in result_list_from_results_commands:
		# Commands in the file_commands group do not update ebook files, so have to use the actual
		# results files for the list of files to compare. The other commands can either create
		# files that don't previously exist or rename files, so they also have to use the actual
		# results files to get the list of files to compare.
		results_files = get_files(results_dir)
	else:
		# The other test groups using this function get the list of files to compare from the
		# input directory, but the actual files compared are the results files. This keeps the
		# entire epub directory tree from having to be saved to the golden files, and files from
		# having to be compared that aren't impacted by the commands.
		results_files = get_files(in_dir)

	assert results_files

	# Either update the golden files from the results…
	if update_golden:
		# get rid of everything currently in the golden directory
		clean_golden_directory(golden_dir)

		# copy each results file to the golden directory, automatically creating any needed
		# subdirectories in the golden tree
		for file in results_files:
			try:
				shutil.copy(results_dir / file, golden_dir / file)
			except FileNotFoundError:
				golden_file_dir = (golden_dir / file).parent
				golden_file_dir.mkdir(parents=True, exist_ok=True)
				shutil.copy(results_dir / file, golden_dir / file)
				continue
	# … or check all the results files against the existing golden files
	else:
		# Get the golden files
		golden_files = get_files(golden_dir)
		assert golden_files

		# get the list of files in both results/golden, and the list in one but not the other
		results_same = list(set(results_files).intersection(golden_files))
		results_diffs = list(set(results_files).symmetric_difference(golden_files))

		# files in both are compared for equality
		for file in results_same:
			# image files aren't utf-8, and a dump isn't useful, so let filecmp handle them
			if file.suffix in (".bmp", ".jpg", ".png", ".tif"):
				if not filecmp.cmp(results_dir / file, golden_dir / file):
					assert "" == f"Results image file {file} different than golden file"
			else:
				with open(golden_dir / file, encoding="utf-8") as gfile:
					golden_text = gfile.read()
				with open(results_dir / file, encoding="utf-8") as rfile:
					results_text = rfile.read()
				assert results_text == golden_text

		# files in one but not the other are errors
		for file in results_diffs:
			if file not in results_files:
				assert "" == f"Golden file {file} not present in results"
			else:
				assert "" == f"Extraneous results file {file} not present in golden files"

	return True

def output_is_golden(results: str, golden_file: Path, update_golden: bool) ->bool:
	"""
	Verify the output from a test matches the contents of the golden file.
	"""
	__tracebackhide__ = True # pylint: disable=unused-variable

	if update_golden:
		with open(golden_file, "w", encoding="utf-8") as file:
			file.write(results)

	# Output of stdout should match expected output
	with open(golden_file, encoding="utf-8") as file:
		assert file.read() == results

	return True
