"""
Test the build command.
Testing build is done in two steps:
1. The `build` command itself is run, either using the default command, or a command-file. The 
   output is directed to book_directory/build.
2. The `extract-epub` command is run against the generated compatible .epub. The output is directed
   to book_directory/extract.

The build files are verified against the golden build files for existence only.
The extract files are verified against the golden extract files, that they exist in both places and
are identical.
"""

import os
from pathlib import Path
import pytest
from helpers import assemble_testbook, must_run, build_is_golden

test_command = "build"	# pylint: disable=invalid-name
module_directory = Path(__file__).parent / test_command
module_tests = []

# the module directory should not be created until at least one test exists
if module_directory.is_dir():
	# build can have multiple tests, each contained in a separate subdirectory
	for directory_entry in os.scandir(module_directory):
		if directory_entry.is_dir():
			module_tests.append([test_command, os.path.basename(directory_entry)])
	module_tests.sort()

# pass the plain command and subdir name so the test ids are easy to read, e.g. build-test-1
@pytest.mark.parametrize("command, test", module_tests)

def test_build_command(testbook__directory: Path, work__directory: Path, command: str, test: Path, update_golden: bool):
	"""
	Run each command on the input content and validate that the transformed text
	matches the expected output content.
	"""

	# the default command to call
	command_to_use = command
	test_directory = module_directory / test
	# if a file exists in test_directory with the same name as {command}-command, e.g.
	# build-command, the first line should contain the command to use, with any arguments, e.g.
	# `build --arg1 --arg2`
	command_file = test_directory / (command + "-command")
	if command_file.is_file():
		with open(command_file, "r", encoding="utf-8") as cfile:
			command_full = cfile.readline().strip()

		# make sure command is present
		if command in command_full:
			command_to_use = command_full
		else:
			assert "" == f"{command_full} does not contain the command '{command}'"

	# contains the files specific to the particular test being run
	in_directory = test_directory / "in"
	# contains the full ebook structure, with the in_directory files copied over the test ebook files
	book_directory = assemble_testbook(testbook__directory, in_directory, work__directory)
	# the directory where the build output will be directed
	build_directory = book_directory / "build"
	# the directory where the extract-ebook output will be directed
	extract_directory = book_directory / "extract"
	# contains the "golden" files, i.e. the files as they should look after the test
	golden_directory = test_directory / "golden"

	# run the build command itself
	must_run(f"se {command_to_use} --output={build_directory} {book_directory}")
	# extract the compatible epub, if one was created
	epub_glob = build_directory.glob("*.epub")
	for epub_file in epub_glob:
		if "_advanced" not in epub_file.name:
			must_run(f"se extract-ebook --output={extract_directory} {epub_file}")
			break

	# verify the build and extract files against the golden ones
	build_is_golden(build_directory, extract_directory, golden_directory, update_golden)
