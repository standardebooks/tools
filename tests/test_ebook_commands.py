"""
Tests for commands that transform epub text files, and require a substantially
complete ebook directory structure to do so.
This includes:
	build, build-ids, build-images, prepare-release, recompose-epub, renumber-endnotes,
	shift-endnotes, shift-illustrations
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_testbook, must_run, files_are_golden

module_directory = Path(__file__).parent / "ebook_commands"
module_tests = []

# the directory can't exist until at least one test exists
if module_directory.is_dir():
	# the commands being tested are the list of subdirectories
	test_commands = [os.path.basename(test_entry.path) for test_entry in os.scandir(module_directory) if test_entry.is_dir()]

	# each command can have multiple tests, each contained in a separate subdirectory
	for test_command in test_commands:
		for directory_entry in os.scandir(module_directory / test_command):
			if directory_entry.is_dir():
				module_tests.append([test_command, os.path.basename(directory_entry)])
	module_tests.sort()
@pytest.mark.parametrize("command, test", module_tests)

def test_ebook_commands(testbook__directory: Path, work__directory: Path, command: str, test: Path, update_golden: bool):
	"""
	Run each command on the input content and validate that the transformed text
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

	in_directory = test_directory / "in"
	golden_directory = test_directory / "golden"
	book_directory = assemble_testbook(testbook__directory, in_directory, work__directory)

	must_run(f"se {command_to_use} {book_directory}")
	files_are_golden(in_directory, book_directory, golden_directory, update_golden)
