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
	for module_info in pkgutil.iter_modules(se.commands.__path__):
		command = module_info.name.replace("_", "-")
		if command != "version":
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
	parser.add_argument("-p", "--plain", dest="plain_output", action="store_true", help="print plain text output, without tables or formatting")
	parser.add_argument("-v", "--version", action="store_true", help="print version number and exit")
	parser.add_argument("command", metavar="COMMAND", choices=commands, help="one of: " + " ".join(commands))
	parser.add_argument("arguments", metavar="ARGS", nargs="*", help="arguments for the subcommand")

	# We do some hand-parsing of high-level args, because argparse
	# can expect flags at any point in the command. We'll pass any args up to
	# and including the subcommand to the main argparse instance, then pass
	# the subcommand and its args to the final function we call.
	main_args = []
	subcommand_args = []
	parsing_subcommand = False
	for arg in sys.argv[1:]:
		if not parsing_subcommand and arg.startswith("-"):
			main_args.append(arg)
		elif not parsing_subcommand and not arg.startswith("-"):
			main_args.append(arg)
			subcommand_args.append(arg)
			parsing_subcommand = True
		elif parsing_subcommand:
			subcommand_args.append(arg)

	args = parser.parse_args(main_args)

	# Change argv to our subcommand values, so that arg parsing by child functions works as expected
	sys.argv = subcommand_args

	command_name = args.command.replace("-", "_")
	command_module = f"se.commands.{command_name}"
	if command_name == "help":
		command_function = "se_help"  # Avoid name conflict with built-in function
	else:
		command_function = command_name

	# Import command module and call command entrypoint
	module = importlib.import_module(command_module)

	try:
		sys.exit(getattr(module, command_function)(args.plain_output))
	except KeyboardInterrupt:
		sys.exit(130) # See http://www.tldp.org/LDP/abs/html/exitcodes.html
