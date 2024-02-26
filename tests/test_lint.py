"""
Tests for the lint command; each lint error has one test directory with a name equal
to the lint error id, e.g. c-001, t-040, etc.
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_testbook, run, output_is_golden

lint_subtypes = ["css", "filesystem", "metadata", "semantic", "typography", "typos", "xhtml"]
module_directory = Path(__file__).parent / "lint"
module_tests = []

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

def test_lint(testbook__directory: Path, work__directory: Path, lint_subtype: str, test: str, update_golden: bool, capfd): # pylint: disable=redefined-outer-name
	"""
	Run lint command on assembled test book, i.e. stock test book plus files from test,
	and capture output to compare with "golden" output.
	"""
	test_directory = module_directory / lint_subtype / test
	in_directory = test_directory / "in"
	book_directory = assemble_testbook(testbook__directory, in_directory, work__directory)

	result = run(f"se --plain lint {book_directory}")

	# All books with errors should return a non-zero return code
	assert result.returncode != 0

	# Output of stderr should always be empty
	out, err = capfd.readouterr()
	assert err == ""

	golden_file = test_directory / "golden" / f"{test}-out.txt"
	assert output_is_golden(out, golden_file, update_golden)
