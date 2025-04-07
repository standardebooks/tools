"""
Tests for commands that run against a draft ebook and produce output to stdout.
The stdout commands are:
	build-loi, build-manifest, build-spine, build-title, build-toc, css-select, 
	find-mismatched-dashes, find-mismatched-diacritics, find-unusual-characters, help,
	recompose-epub, unicode-names, word-count, xpath

The build-* commands are special in that they can either update existing files, or they can,
with an argument, generate their output to stdout. Thus, to test them here, in the stdout
group, they require the `--stdout` argument. It is automatically added if there is no command
file, otherwise the command file must include it.

The command `unicode_names` is special in that it takes a string as input rather than an ebook
directory. Thus it also requires a command file, with the command and input string parameter.

The command `help` is special in that it does not take any input.
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_draftbook, must_run, output_is_golden

no_ebook_directory_commands = ["unicode-names", "help"]
stdout_argument_commands = ["build-loi", "build-manifest", "build-spine", "build-title", "build-toc"]
command_file_commands = stdout_argument_commands + ["unicode-names"]
module_directory = Path(__file__).parent / "stdout_commands"
module_tests = []

# the module directory should not be created until at least one test exists
if module_directory.is_dir():
	# the commands being tested are the list of subdirectories
	test_commands = [os.path.basename(s.path) for s in os.scandir(module_directory) if s.is_dir()]

	# each command can have multiple tests, each contained in a separate subdirectory
	for test_command in test_commands:
		for directory_entry in os.scandir(module_directory / test_command):
			if directory_entry.is_dir():
				module_tests.append([test_command, os.path.basename(directory_entry)])
	module_tests.sort()

# pass the plain command and test name so the test ids are easy to read, e.g. build-manifest-test-1
@pytest.mark.parametrize("command, test", module_tests)

def test_stdout_commands(draftbook__directory: Path, work__directory: Path, command: str, test: Path, update_golden: bool, capfd):
	"""
	Run each command on assembled draft book, capture output and compare it to "golden" output
	"""

	# the default command to call is the name of the command directory
	command_to_use = command
	test_directory = module_directory / command / test
	# if a file exists in test_directory with the name of {command}-command, e.g. word-count-command,
	# the first line should contain the command to use, with any arguments, e.g.`command --arg1`
	command_file = test_directory / (command + "-command")
	if command_file.is_file():
		with open(command_file, "r", encoding="utf-8") as cfile:
			command_full = cfile.readline().strip()
		# the command must be in the command file
		if command not in command_full:
			assert "" == f"'{command_full}' does not contain the command '{command}'"
		# for the commands requiring --stdout, it must be in the command file
		elif command in stdout_argument_commands and "--stdout" not in command_full:
			assert "" == f"{command_full} does not contain --stdout argument"
		else:
			command_to_use = command_full
	# these commands require a command file
	elif command in command_file_commands:
		assert "" == f"{command} requires a command file and none was found"
	# no command file, automatically add the --stdout argument to the commands requiring it
	elif command in stdout_argument_commands:
		command_to_use += " --stdout"

	# these commands don't have any input files and thus don't need/use the book directory
	if command in no_ebook_directory_commands:
		must_run(f"se {command_to_use}")
	else:
		# contains the files specific to the particular test being run
		in_directory = test_directory / "in"
		# contains the full ebook structure, with the in_directory files copied over the draft ebook files
		book_directory = assemble_draftbook(draftbook__directory, in_directory, work__directory)
		must_run(f"se {command_to_use} {book_directory}")

	# Output of stderr should always be empty
	out, err = capfd.readouterr()
	assert err == ""

	golden_file = test_directory / "golden" / f"{command}-{test}-out.txt"
	assert output_is_golden(out, golden_file, update_golden)
