"""
Tests for commands that transform epub text files and require a substantially
complete ebook directory structure.
These include:
	build-ids, build-images, prepare-release, recompose-epub, renumber-endnotes, shift-endnotes,
	shift-illustrations
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_testbook, must_run, files_are_golden

module_directory = Path(__file__).parent / "ebook_commands"
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

# pass the plain command and subdir name so the test ids are easy to read, e.g. build-ids-test-1
@pytest.mark.parametrize("command, test", module_tests)

def test_ebook_commands(testbook__directory: Path, work__directory: Path, command: str, test: Path, update_golden: bool):
	"""
	Run each command on the input content and validate that the transformed text
	matches the expected output content.
	"""

	# the default command to call is the name of the command directory
	command_to_use = command
	test_directory = module_directory / command / test
	# if a file exists in test_directory with the name of {command}-command, e.g. build-ids-command,
	# each line should contain the command to use, with any arguments, e.g. `command --arg1 --arg2`
	command_file = test_directory / (command + "-command")
	if command_file.is_file():
		with open(command_file, "r", encoding="utf-8") as cfile:
			commands_full = [line.strip() for line in cfile.readlines() if line.strip() != ""]
		# make sure command is present in at least one line
		if any(command in line for line in commands_full):
			commands_to_use = commands_full
		else:
			assert "" == f"{command_file} does not contain the command '{command}'"
	else:
		commands_to_use = [f"{command} {{book_directory}}"]

	# contains the files specific to the particular test being run
	in_directory = test_directory / "in"
	# contains the full ebook structure, with the in_directory files copied over the test ebook files
	book_directory = assemble_testbook(testbook__directory, in_directory, work__directory)
	# contains the "golden" files, i.e. the files as they should look after the test
	golden_directory = test_directory / "golden"

	for command_to_use in commands_to_use:
		command_to_use = command_to_use.format(book_directory=book_directory)
		must_run(f"se {command_to_use}")
	files_are_golden(golden_directory, book_directory, golden_directory, update_golden)
