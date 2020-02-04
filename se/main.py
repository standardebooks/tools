"""
Entrypoint for se command
"""

import argparse
import importlib
import pkgutil
import sys
from typing import List

import se.cmd


def main():
	"""
	Entry point for the main `se` executable.

	This function delegates subcommands (like `se typogrify`) to various functions within this module.

	Some more complex commands (like `create-draft` or `build` are broken out into their own files for
	readability and maintainability.
	"""

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

	cmd_name = args.command.replace("-", "_")
	cmd_module = "se.cmd." + cmd_name
	cmd_function = "cmd_" + cmd_name

	# Import command module and call command entrypoint
	module = importlib.import_module(cmd_module)
	ret_code = getattr(module, cmd_function)()

	sys.exit(ret_code)

def get_commands() -> List[str]:
	"""
	Helper function to generate a list of available commands from all of the submodules in the se.cmd package
	"""

	commands = []
	for module_info in pkgutil.iter_modules(se.cmd.__path__): # type: ignore # mypy issue 1422
		command = module_info.name.replace("_", "-")
		commands.append(command)
	commands.sort()

	return commands
