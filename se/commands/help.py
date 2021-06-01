"""
This module implements the `se help` command.
"""

from se.main import get_commands


def se_help(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se help`

	help() is a built-in function so this function is called se_help().
	"""

	commands = get_commands()

	print("The following commands are available:")

	for command in commands:
		print(command)

	return 0
