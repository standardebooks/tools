"""
Tests for lint command.
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_book, run, output_is_golden

# get list of tests from the subdirectory names (outside the function, so data_dir fixture isn't available)
test_names = [os.path.basename(s.path) for s in os.scandir(Path(__file__).parent / "data/lint") if s.is_dir()]
@pytest.mark.parametrize("test_name", test_names)

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
