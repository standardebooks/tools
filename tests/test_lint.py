"""
Tests for the lint command; each lint error has one test directory with a name equal
to the lint error id, e.g. c-001, t-040, etc.
"""

import os
import shutil
from pathlib import Path
import pytest
from helpers import assemble_testbook, fail_test, run, output_is_golden # pylint: disable=import-error
from se.se_epub import SeEpub

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

@pytest.mark.parametrize("translation, has_translator, missing_year", [
	("", False, False),
	("", True, False),
	("It was translated from French by", True, True),
	("It was translated from French in <time>1900</time> by", True, False),
	('It was translated from French in <time datetime="1900">1900</time> by', True, False),
	("It was translated from French in <time>TRANSLATION_YEAR</time> by", True, True),
	("It was translated from French in 1900 by", True, False),
	("It was translated from French between <time>1840</time> and <time>1999</time> by", True, False),
	("It was translated from French between <time>1840</time> and by", True, True),
	("It was translated from French in TRANSLATION_YEAR by", True, True),
	("It was translated from French in the nineteenth century by", True, True),
	("It was translated from French by a translator born in <time>1900</time>,", True, True),
	("They were translated from Italian and French between <time>1894</time> and <time>1923</time> by", True, False),
	("It was translated from Norwegian in <time>1879</time> and <time>1893</time> by", True, False),
	("It was translated from German and released to the public domain in <time>2001</time> by", True, False),
	("It was translated from Middle High German in <time>1889</time> by", True, False),
	("It was translated from\n\t\t\tFrench in <time>1900</time> by", True, False),
])
def test_colophon_translation_year(testbook__directory: Path, tmp_path: Path, translation: str, has_translator: bool, missing_year: bool) -> None:
	"""
	Require translation dates without accepting unrelated dates elsewhere in the colophon.
	"""

	book_directory = tmp_path / "testbook"
	shutil.copytree(testbook__directory, book_directory)
	if has_translator:
		metadata_path = book_directory / "src/epub/content.opf"
		metadata = metadata_path.read_text(encoding="utf-8")
		metadata = metadata.replace("</metadata>", '<meta property="role" refines="#author" scheme="marc:relators">trl</meta></metadata>')
		metadata_path.write_text(metadata, encoding="utf-8")

	if translation:
		colophon_path = book_directory / "src/epub/text/colophon.xhtml"
		colophon = colophon_path.read_text(encoding="utf-8")
		colophon = colophon.replace("</a>.</p>", f"</a>.<br/>\n\t\t\t{translation}<br/>\n\t\t\t<b>An Anonymous Volunteer</b>.</p>", 1)
		colophon_path.write_text(colophon, encoding="utf-8")

	messages = SeEpub(book_directory).lint(skip_lint_ignore=True)
	assert ("m-072" in [message.code for message in messages]) == missing_year
	assert ("m-025" in [message.code for message in messages]) == (has_translator and not translation)
