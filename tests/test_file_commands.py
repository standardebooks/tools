"""
Tests for commands that take zero or more files as input and produce one or more ouptut files.
This includes:
	create-draft, extract-ebook, split-file, unicode-names
"""

import os
from pathlib import Path
import shutil
import pytest
from helpers import must_run, files_are_golden

module_directory = Path(__file__).parent / "file_commands"
module_tests = []

# the directory can't exist until at least one test exists
if module_directory.is_dir():
	# the commands being tested are the list of subdirectories
	test_commands = [os.path.basename(s.path) for s in os.scandir(module_directory) if s.is_dir()]

	# each command can have multiple tests, each contained in a separate subdirectory
	for test_command in test_commands:
		for directory_entry in os.scandir(module_directory / test_command):
			if directory_entry.is_dir():
				module_tests.append([test_command, os.path.basename(directory_entry)])
	module_tests.sort()

# pass the plain command and subdir name so the test ids are easy to read, e.g. typogrify-test-1
@pytest.mark.parametrize("command, test", module_tests)

def test_filecommands(work__directory: Path, command: str, test: Path, update_golden: bool):
	"""
	Run each command on the input content and validate that the output of the command
	matches the expected output content.
	"""
	# the default command to call is the name of the command directory
	command_to_use = command
	test_directory = module_directory / command / test
	# if a file exists in test_directory with the same name as the {command}-command, e.g. help-command,
	# the first line should contain the full command to use, with any arguments.
	command_file = test_directory / (command + "-command")
	if command_file.is_file():
		with open(command_file, "r", encoding="utf-8") as cfile:
			command_full = cfile.readline().rstrip()
		# make sure command is present
		if command in command_full:
			command_to_use = command_full
		else:
			assert "" == f"'{command_full}' does not contain the command '{command}'"

	# make a directory for the test in the working directory
	in_directory = test_directory / "in"
	golden_directory = test_directory / "golden"

	# copy the input files (if any) to a working test directory
	work_test_directory = work__directory / command / test
	shutil.copytree(in_directory, work_test_directory)

	# run the command on that directory and verify the output
	must_run(f"se {command_to_use} {work_test_directory}")
	files_are_golden(work_test_directory, work_test_directory, golden_directory, update_golden)
