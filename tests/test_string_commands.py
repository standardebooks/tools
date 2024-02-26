"""
Tests for simple se commands that take a string as input and output a string as output.
This includes:
	dec2roman, make-url-safe, roman2dec, titlecase, version
"""

import os
from pathlib import Path
import pytest
from helpers import must_run
import se

test_directory = Path(__file__).parent / "string_commands"
cmds = [os.path.basename(fname) for fname in os.scandir(test_directory) if fname.is_file()]
@pytest.mark.parametrize("cmd", cmds)

def test_stringcmds(cmd: str, capfd):
	"""
	Execute command and check output.
	"""
	cmd_file = test_directory / cmd
	with open(cmd_file, "r", encoding="utf-8") as cfile:
		for line in cfile:
			# each line in the file contains an input string and a "golden" string
			in_str, golden_str = line.split(",")
			must_run(f"se {cmd} {in_str}")
			out, _ = capfd.readouterr()
			assert out.rstrip() == golden_str.strip()

def test_version(capfd):
	"""
	Verify that the version command returns the version. This is a separate test within
	the module because it uses an SE internal command to return the "golden" text.
	"""
	must_run("se --version")
	out, _ = capfd.readouterr()
	assert out.startswith(se.VERSION)
