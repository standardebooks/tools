"""
Tests for commands that will run against a draft ebook and produce output to stdout.
These include:
	build-manifest, build-spine, build-toc, css-select, find-mismatched-dashes,
	find-mismatched-diacritics, find-unusual-characters, help, unicode-names,
	word-count, xpath
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_draftbook, must_run, output_is_golden

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

	# the default command to call is the name of the cmd directory
	command_to_use = command
	test_directory = module_directory / command / test
	# if a file exists in test_directory with the name of {command}-command, e.g. word-count-command,
	# the first line should contain the command to use, with any arguments, e.g.`command --arg1`
	command_file = test_directory / (command + "-command")
	if command_file.is_file():
		with open(command_file, "r", encoding="utf-8") as cfile:
			command_full = cfile.readline().rstrip()
		# make sure the command is present in the string
		if command in command_full:
			command_to_use = command_full
		else:
			assert "" == f"'{command_full}' does not contain the command '{command}'"

	# help doesn't have any input files and doesn't need/use a ebook directory structure
	if command == "help":
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
	print(f"testdir: {test_directory}, golden: {golden_file}")
	assert output_is_golden(out, golden_file, update_golden)
