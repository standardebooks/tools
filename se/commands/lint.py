"""
This module implements the `se lint` command.
"""

import argparse
from textwrap import wrap

from colored import stylize, fg, bg, attr
import regex
import terminaltables

import se
from se.se_epub import SeEpub


def _print_table(table_data: list, wrap_column: int = None) -> None:
	"""
	Helper function to print a table to the console.

	INPUTS
	table_data: A list where each entry is a list representing the columns in a table
	wrap_column: The 0-indexed column to wrap

	OUTPUTS
	None
	"""

	table = terminaltables.SingleTable(table_data)
	table.inner_heading_row_border = False
	table.inner_row_border = True
	table.justify_columns[0] = "center"

	# Calculate newlines
	if wrap_column is not None:
		max_width = table.column_max_width(wrap_column)
		for row in table_data:
			row[wrap_column] = "\n".join(wrap(row[wrap_column], max_width))

	print(table.table)

def lint() -> int:
	"""
	Entry point for `se lint`
	"""

	parser = argparse.ArgumentParser(description="Check for various Standard Ebooks style errors.")
	parser.add_argument("-p", "--plain", action="store_true", help="print plain text output, without tables or colors")
	parser.add_argument("-n", "--no-colors", dest="colors", action="store_false", help="do not use colored output")
	parser.add_argument("-s", "--skip-lint-ignore", action="store_true", help="ignore rules in se-lint-ignore.xml file")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	first_output = True
	return_code = 0

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
			messages = se_epub.lint(args.skip_lint_ignore)
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
				print(stylize(str(se_epub.path), attr("reverse")))

		# Print the table
		if messages:
			return_code = se.LintFailedException.code

			if args.plain:
				for message in messages:
					label = "Manual Review:"

					if message.message_type == se.MESSAGE_TYPE_ERROR:
						label = "Error:"

					print(f"{message.code} {label} {message.filename} {message.text}")

					if message.submessages:
						for submessage in message.submessages:
							print(f"\t{submessage}")
			else:
				table_data.append([stylize("Code", attr("bold")), stylize("Severity", attr("bold")), stylize("File", attr("bold")), stylize("Message", attr("bold"))])

				for message in messages:
					alert = "Manual Review"

					if message.message_type == se.MESSAGE_TYPE_ERROR:
						alert = "Error"

					message_text = message.text

					if args.colors:
						if message.message_type == se.MESSAGE_TYPE_ERROR:
							alert = stylize(alert, fg("red"))
						else:
							alert = stylize(alert, fg("yellow"))

						# By convention, any text within the message text that is surrounded in backticks
						# is rendered in blue
						message_text = regex.sub(r"`(.+?)`", stylize(r"\1", fg("light_blue")), message_text)

					table_data.append([message.code, alert, message.filename, message_text])

					if message.submessages:
						for submessage in message.submessages:
							table_data.append([" ", " ", "→", f"{submessage}"])

				_print_table(table_data, 3)

		if args.verbose and not messages:
			if args.plain:
				print("OK")
			else:
				table_data.append([stylize(" OK ", bg("green") + fg("white") + attr("bold"))])

				_print_table(table_data)

	return return_code
