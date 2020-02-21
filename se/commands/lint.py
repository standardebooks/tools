"""
This module implements the `se lint` command.
"""

import argparse

import regex
from termcolor import colored

import se
from se.se_epub import SeEpub


def lint() -> int:
	"""
	Entry point for `se lint`
	"""

	parser = argparse.ArgumentParser(description="Check for various Standard Ebooks style errors.")
	parser.add_argument("-p", "--plain", action="store_true", help="print plain text output, without tables or colors")
	parser.add_argument("-n", "--no-colors", dest="colors", action="store_false", help="do not use colored output")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	first_output = True
	return_code = 0

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
			messages = se_epub.lint()
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

		table_data = []

		# Print a separator newline if more than one table is printed
		if not first_output and (args.verbose or messages):
			print("")
		elif first_output:
			first_output = False

		# Print the table header
		if args.verbose or (messages and len(args.directories) > 1):
			if args.plain:
				print(se_epub.path)
			else:
				print(colored(str(se_epub.path), "white", attrs=["reverse"]))

		# Print the table
		if messages:
			return_code = se.LintFailedException.code

			if args.plain:
				for message in messages:
					label = "Manual Review:"

					if message.message_type == se.MESSAGE_TYPE_ERROR:
						label = "Error:"

					print(f"{label} {message.filename} {message.text}")

					if message.submessages:
						for submessage in message.submessages:
							print(f"\t{submessage}")
			else:
				for message in messages:
					alert = "Manual Review"

					if message.message_type == se.MESSAGE_TYPE_ERROR:
						alert = "Error"

					message_text = message.text

					if args.colors:
						if message.message_type == se.MESSAGE_TYPE_ERROR:
							alert = colored(alert, "red")
						else:
							alert = colored(alert, "yellow")

						# By convention, any text within the message text that is surrounded in backticks
						# is rendered in blue
						message_text = regex.sub(r"`(.+?)`", colored(r"\1", "blue"), message_text)

					table_data.append([alert, message.filename, message_text])

					if message.submessages:
						for submessage in message.submessages:
							table_data.append([" ", "→", f"{submessage}"])

				se.print_table(table_data, 2)

		if args.verbose and not messages:
			if args.plain:
				print("OK")
			else:
				table_data.append([colored("OK", "green", attrs=["reverse"])])

				se.print_table(table_data)

	return return_code
