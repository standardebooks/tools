"""
Tests for commands that transform epub text files and only need a draft ebook to run.
The draft commands are:
	british2american, build-loi, build-manifest, build-spine, build-title, build-toc,
	clean, hyphenate, modernize-spelling, semanticate, typogrify

The build-* commands are special in that they can either update existing files, or they can, with an
argument, generate their output to stdout. To test them here, in the draft group, they have to update
files, so disallow `--stdout` in any command file.
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_draftbook, must_run, files_are_golden

module_directory = Path(__file__).parent / "draft_commands"
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

# pass the plain command and subdir name so the test ids are easy to read, e.g. typogrify-test-1
@pytest.mark.parametrize("command, test", module_tests)

def test_draft_commands(draftbook__directory: Path, work__directory: Path, command: str, test: Path, update_golden: bool):
	"""
	Run each command on the input content and validate that the transformed text
	matches the expected output content.
	"""

	# the default command to call is the name of the command directory
	command_to_use = command
	test_directory = module_directory / command / test
	# if a file exists in test_directory with the name of {command}-command, e.g. clean-command,
	# the first line should contain the command to use, with any arguments, e.g.`command --arg1`
	command_file = test_directory / (command + "-command")
	if command_file.is_file():
		with open(command_file, "r", encoding="utf-8") as cfile:
			command_full = cfile.readline().strip()
		# the command must be in the command file
		if command not in command_full:
			assert "" == f"'{command_full}' does not contain the command '{command}'"
		# make sure the --stdout argument isn't part of the command file
		elif "--stdout" in command_full:
			assert "" == f"{command_full} cannot contain --stdout argument"
		else:
			command_to_use = command_full

	# contains the files specific to the particular test being run
	in_directory = test_directory / "in"
	# contains the full ebook structure, with the in_directory files copied over the draft ebook files
	book_directory = assemble_draftbook(draftbook__directory, in_directory, work__directory)
	# contains the "golden" files, i.e. the files as they should look after the test
	golden_directory = test_directory / "golden"

	# run the command against the book directory
	must_run(f"se {command_to_use} {book_directory}")
	# verify the result files against the golden ones
	files_are_golden(command, in_directory, book_directory, golden_directory, update_golden)
