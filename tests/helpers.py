"""
Common helper functions for tests.
"""

import shlex
import shutil
import subprocess
from pathlib import Path
import filecmp
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

def clean_golden_directory(golden_dir: Path) -> None:
	"""
	Delete all files and subdirectory trees in a passed golden directory

	INPUTS
	golden_dir: the golden directory to be cleaned
	"""

	golden_glob = golden_dir.glob("*")
	for gfd in golden_glob:
		if gfd.is_file():
			gfd.unlink()
		elif gfd.is_dir():
			shutil.rmtree(gfd)

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

	# Get the list of build files (only a single level)
	build_files = []
	build_glob = build_dir.glob("*")
	build_files = [bf.relative_to(build_dir) for bf in build_glob if bf.is_file()]
	assert build_files

	# Get the list of extract files (directory tree)
	extract_files = []
	extract_glob = extract_dir.glob("**/*")
	extract_files = [ef.relative_to(extract_dir) for ef in extract_glob if ef.is_file()]
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
		golden_build_files = []
		golden_build_glob = golden_build_dir.glob("*")
		golden_build_files = [gbf.relative_to(golden_build_dir) for gbf in golden_build_glob if gbf.is_file()]
		assert golden_build_files

		# Get the list of golden extract files (directory tree)
		golden_extract_files = []
		golden_extract_glob = golden_extract_dir.glob("**/*")
		golden_extract_files = [gef.relative_to(golden_extract_dir) for gef in golden_extract_glob if gef.is_file()]
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
		# get rid of everything currently in the golden directory
		clean_golden_directory(golden_dir)

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
