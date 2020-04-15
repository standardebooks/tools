"""
This file contains the entry point for the `se` command.
"""

import argparse
import importlib
import pkgutil
import sys
from typing import List

import se.commands


def get_commands() -> List[str]:
	"""
	Helper function to generate a list of available commands from all of the submodules in the se.cmd package
	"""

	commands = []
	for module_info in pkgutil.iter_modules(se.commands.__path__): # type: ignore # mypy issue 1422
		command = module_info.name.replace("_", "-")
		commands.append(command)
	commands.sort()

	return commands

def main() -> None:
	"""
	Entry point for the main `se` executable.

	This function delegates subcommands (like `se typogrify`) to individual submodules under `se.commands`.
	"""

	# If we're asked for the version, short circuit and exit
	if len(sys.argv) == 2 and (sys.argv[1] == "-v" or sys.argv[1] == "--version"):
		module = importlib.import_module("se.commands.version")
		sys.exit(getattr(module, "version")())

	commands = get_commands()

	parser = argparse.ArgumentParser(description="The entry point for the Standard Ebooks toolset.")
	parser.add_argument("-v", "--version", action="store_true", help="print version number and exit")
	parser.add_argument("command", metavar="COMMAND", choices=commands, help="one of: " + " ".join(commands))
	parser.add_argument("arguments", metavar="ARGS", nargs="*", help="arguments for the subcommand")
	args = parser.parse_args(sys.argv[1:2])

	# Remove the command name from the list of passed args.
	sys.argv.pop(1)

	# Change the command name so that argparse instances in child functions report the correct command on help/error.
	sys.argv[0] = args.command

	command_name = args.command.replace("-", "_")
	command_module = f"se.commands.{command_name}"
	if command_name == "help":
		command_function = "se_help"  # Avoid name conflict with built-in function
	else:
		command_function = command_name

	# Import command module and call command entrypoint
	module = importlib.import_module(command_module)

	try:
		sys.exit(getattr(module, command_function)())
	except KeyboardInterrupt:
		sys.exit(130) # See http://www.tldp.org/LDP/abs/html/exitcodes.html
