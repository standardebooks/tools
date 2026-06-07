"""
Tests for the lint command; each lint error has one test directory with a name equal
to the lint error id, e.g. c-001, t-040, etc.
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_testbook, fail_test, run, output_is_golden # pylint: disable=import-error

lint_subtypes = ["css", "filesystem", "metadata", "semantic", "typography", "typos", "xhtml"]
module_directory = Path(__file__).parent / "lint"
module_tests: list[list[str]] = []

# get list of each subtype's tests from the subdirectory names
for lint_subtype in lint_subtypes:
	lint_subtype_directory = module_directory / lint_subtype
	# the directory can't exist until at least one test exists
	if lint_subtype_directory.is_dir():
		for directory_entry in os.scandir(lint_subtype_directory):
			if directory_entry.is_dir():
				module_tests.append([lint_subtype, os.path.basename(directory_entry)])

module_tests.sort()
@pytest.mark.parametrize("lint_subtype, test", module_tests)

def test_lint(testbook__directory: Path, work__directory: Path, lint_subtype: str, test: str, update_golden: bool, capfd: pytest.CaptureFixture[str]): # pylint: disable=redefined-outer-name
	"""
	Run lint command on assembled test book, i.e. stock test book plus files from test,
	and capture output to compare with "golden" output.
	"""
	test_directory = module_directory / lint_subtype / test
	test_context = f"lint/{lint_subtype}/{test}"
	in_directory = test_directory / "in"
	book_directory = assemble_testbook(testbook__directory, in_directory, work__directory)

	result = run(f"se --plain lint {book_directory}")

	# All books with errors should return a non-zero return code
	if result.returncode == 0:
		fail_test(f"Test: {test_context}\n\nExpected lint to return a non-zero exit code.")
	# Exit codes 1 and 2 indicate a problem with `se lint` itself
	if result.returncode in {1, 2}:
		fail_test(f"Test: {test_context}\n\nLint returned error code {result.returncode}, which indicates a problem with `se lint` itself.")

	# Output of stderr should always be empty
	out, err = capfd.readouterr()
	if err:
		fail_test(f"Test: {test_context}\n\nStderr was not empty.\n\n{err}")

	golden_file = test_directory / "golden" / f"{test}-out.txt"
	output_is_golden(out, golden_file, update_golden, test_context)
