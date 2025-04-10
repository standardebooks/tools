"""
Tests for commands that take zero or one file as input and produce one or more output files.
The file commands are:
	create-draft, extract-ebook, split-file

NOTE: Changes to this list should be reflected in the file_commands variable in the files_are_golden
helper function.
"""

import os
from pathlib import Path
import pytest
from helpers import must_run, files_are_golden

module_directory = Path(__file__).parent / "file_commands"
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

# pass the plain command and test name so the test ids are easy to read, e.g. create-draft-test-1
@pytest.mark.parametrize("command, test", module_tests)

def test_file_commands(work__directory: Path, command: str, test: Path, update_golden: bool):
	"""
	Run each command on the input content and validate that the output of the command
	matches the expected output content.
	"""

	# the default command to call is the name of the command directory
	command_to_use = command
	test_directory = module_directory / command / test
	# if a file exists in test_directory with the name of {command}-command, e.g. create-draft-command,
	# the first line should contain the command to use, with any arguments, e.g.`command --arg1`
	command_file = test_directory / (command + "-command")
	if command_file.is_file():
		with open(command_file, "r", encoding="utf-8") as cfile:
			command_full = cfile.readline().strip()
		# make sure command is present
		if command in command_full:
			command_to_use = command_full
		else:
			assert "" == f"'{command_full}' does not contain the command '{command}'"

	# contains the files specific to the particular test being run
	in_directory = test_directory / "in"
	# contains the "golden" files, i.e. the files as they should look after the test
	golden_directory = test_directory / "golden"

	# The file commands either take no input (create-draft) or a single file (extract-ebook,
	# split-file), rather than a directory. Get the name of the file to pass to the must_run
	# command rather than a directory as in the other test groups.
	if command != "create-draft":
		in_glob = in_directory.glob("*")
		for infile in in_glob:
			if infile.is_file():
				command_to_use += f" {infile}"
				break

	# run the command on that file and verify the output
	must_run(f"se {command_to_use}")
	files_are_golden(command, in_directory, work__directory, golden_directory, update_golden)
