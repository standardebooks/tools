"""
lint command
"""

import argparse

from termcolor import colored

import se
from se.common import print_error, print_table
from se.se_epub import SeEpub


def cmd_lint() -> int:
	"""
	Entry point for `se lint`
	"""

	parser = argparse.ArgumentParser(description="Check for various Standard Ebooks style errors.")
	parser.add_argument("-p", "--plain", action="store_true", help="print plain output")
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
			print_error(ex)
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
					if message.is_submessage:
						print("\t" + message.text)
					else:
						label = "Manual Review:"

						if message.message_type == se.MESSAGE_TYPE_ERROR:
							label = "Error:"

						print(label, message.filename, message.text)

			else:
				for message in messages:
					if message.is_submessage:
						table_data.append([" ", "→", f"{message.text}"])
					else:
						alert = colored("Manual Review", "yellow")

						if message.message_type == se.MESSAGE_TYPE_ERROR:
							alert = colored("Error", "red")

						table_data.append([alert, message.filename, message.text])

				print_table(table_data, 2)

		if args.verbose and not messages:
			if args.plain:
				print("OK")
			else:
				table_data.append([colored("OK", "green", attrs=["reverse"])])

				print_table(table_data)

	return return_code
