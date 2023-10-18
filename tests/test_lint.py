"""
Tests for lint command.
"""

from pathlib import Path
import pytest
from helpers import assemble_book, run, output_is_golden


@pytest.mark.parametrize("test_name", ["c-006", "clean", "content", "s-058", "glossaries", "elements"])
def test_lint(data_dir: Path, draft_dir: Path, work_dir: Path, capfd, test_name: str, update_golden: bool):
	"""Run lint command on several books with different expected lint output:
		clean   - No errors expected
		content - Errors for a default content.opf
	"""
	text_dir = data_dir / "lint" / test_name
	book_dir = assemble_book(draft_dir, work_dir, text_dir)

	result = run(f"se --plain lint {book_dir}")

	# All books with errors should return a non-zero return code
	if test_name != "clean":
		assert result.returncode != 0

	# Output of stderr should always be empty
	out, err = capfd.readouterr()
	assert err == ""

	# Update golden output files if flag is set
	golden_file = data_dir / "lint" / f"{test_name}-out.txt"
	assert output_is_golden(out, golden_file, update_golden)
