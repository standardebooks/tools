"""
This file contains the entry point for the `se` command.
"""

import argparse
import importlib
import pkgutil
import sys

import se
import se.commands
from se.se_help_formatter import SeHelpFormatter


def get_commands() -> list[str]:
	"""
	Helper function to generate a list of available commands from all of the submodules in the se.cmd package
	"""

	commands: list[str] = []
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

	try:
		# If we're asked for the version, short circuit and exit.
		if len(sys.argv) == 2 and (sys.argv[1] == "-v" or sys.argv[1] == "--version"):
			module = importlib.import_module("se.commands.version")
			sys.exit(getattr(module, "version")())

		commands = get_commands()

		commands_string = ""

		for command in commands:
			commands_string = f"{commands_string}\n\n• [parameter]{command}[/]"

		parser = argparse.ArgumentParser(description="The entry point for the Standard Ebooks toolset.", formatter_class=SeHelpFormatter)
		output_group = parser.add_mutually_exclusive_group()
		output_group.add_argument("--color", dest="color_output", action="store_true", help="Print output in color, even when not connected to an interactive terminal, but not if the [parameter]NO_COLOR[/] environmental variable is set.")
		output_group.add_argument("-p", "--plain", dest="plain_output", action="store_true", help="Print plain text output, without tables, colors, or other formatting. For tabular output but without colors, set the [parameter]NO_COLOR[/] environmental variable to a non-empty value instead of this option.")
		parser.add_argument("-v", "--version", action="store_true", help="Print version number and exit.")
		parser.add_argument("command", metavar="COMMAND", choices=commands, help="The command to execute; one of: " + commands_string)
		parser.add_argument("arguments", metavar="ARGS", nargs="*", help="Arguments for [parameter]<COMMAND>[/].")

		# We do some hand-parsing of high-level arguments, because `argparse` can expect flags at any point in the command. We'll pass any arguments up to and including the subcommand to the main `argparse` instance, then pass the subcommand and its arguments to the final function we call.
		main_args: list[str] = []
		subcommand_args: list[str] = []
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
		se.COLOR_OUTPUT = args.color_output

		# Change `argv` to our subcommand values, so that argument parsing by child functions works as expected.
		sys.argv = subcommand_args

		command_name = args.command.replace("-", "_")
		command_module = f"se.commands.{command_name}"
		if command_name == "help":
			command_function = "se_help"  # Avoid name conflict with built-in function.
		else:
			command_function = command_name

		# Import command module and call command entrypoint.
		module = importlib.import_module(command_module)

		sys.exit(getattr(module, command_function)(args.plain_output))
	except KeyboardInterrupt:
		sys.exit(130) # See <http://www.tldp.org/LDP/abs/html/exitcodes.html>.
