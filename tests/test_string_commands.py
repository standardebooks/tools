"""
Tests for simple se commands that take a string as input and output a string as output.
This includes:
	dec2roman, make-url-safe, roman2dec, titlecase, version
"""

import os
from pathlib import Path
import pytest

from helpers import assert_text_matches, must_run # pylint: disable=import-error

import se


test_directory = Path(__file__).parent / "string_commands"
cmds = [os.path.basename(fname) for fname in os.scandir(test_directory) if fname.is_file()]
@pytest.mark.parametrize("cmd", cmds)

def test_stringcmds(cmd: str, capfd: pytest.CaptureFixture[str]):
	"""
	Execute command and check output.
	"""
	cmd_file = test_directory / cmd
	with open(cmd_file, "r", encoding="utf-8") as cfile:
		for line_number, line in enumerate(cfile, start=1):
			# each line in the file contains an input string and a "golden" string.
			in_str, golden_str = line.split(",")
			must_run(f"se {cmd} {in_str}")
			out, _ = capfd.readouterr()
			assert_text_matches(golden_str.strip(), out.rstrip(), f"{cmd_file}:{line_number}", "command output", f"string_commands/{cmd} line {line_number}")

def test_version(capfd: pytest.CaptureFixture[str]):
	"""
	Verify that the version command returns the version. This is a separate test within
	the module because it uses an SE internal command to return the "golden" text.
	"""
	must_run("se --version")
	out, _ = capfd.readouterr()
	assert out.startswith(se.VERSION)
