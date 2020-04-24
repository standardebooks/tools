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

def _print_table(table_data: list, wrap_column: int = None, max_width: int = None) -> None:
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
		if max_width is None:
			max_width = table.column_max_width(wrap_column)
		for row in table_data:
			row[wrap_column] = "\n".join(wrap(row[wrap_column], max_width))

	print(table.table)

def lint() -> int:
	"""
	Entry point for `se lint`
	"""

	parser = argparse.ArgumentParser(description="Check for various Standard Ebooks style errors.")
	parser.add_argument("-n", "--no-colors", dest="colors", action="store_false", help="do not use colored output")
	parser.add_argument("-p", "--plain", action="store_true", help="print plain text output, without tables or colors")
	parser.add_argument("-s", "--skip-lint-ignore", action="store_true", help="ignore rules in se-lint-ignore.xml file")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("-w", "--wrap", metavar="INTEGER", type=se.is_positive_integer, default=None, help="force lines to wrap at this number of columns instead of auto-wrapping")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	called_from_parallel = se.is_called_from_parallel()
	first_output = True
	return_code = 0

	for directory in args.directories:
		messages = []
		exception = None
		table_data = []
		has_output = False

		try:
			se_epub = SeEpub(directory)
			messages = se_epub.lint(args.skip_lint_ignore)
		except se.SeException as ex:
			exception = ex
			if len(args.directories) > 1:
				return_code = se.LintFailedException.code
			else:
				return_code = ex.code

		# Print a separator newline if more than one table is printed
		if not first_output and (args.verbose or messages or exception):
			print("")
		elif first_output:
			first_output = False

		# Print the table header
		if ((len(args.directories) > 1 or called_from_parallel) and (messages or exception)) or args.verbose:
			has_output = True
			if args.plain:
				print(directory)
			else:
				print(stylize(directory, attr("reverse")))

		if exception:
			has_output = True
			se.print_error(exception)

		# Print the tables
		if messages:
			has_output = True
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

				_print_table(table_data, 3, args.wrap)

		if args.verbose and not messages and not exception:
			if args.plain:
				print("OK")
			else:
				table_data.append([stylize(" OK ", bg("green") + fg("white") + attr("bold"))])

				_print_table(table_data, None, args.wrap)

		# Print a newline if we're called from parallel and we just printed something, to
		# better visually separate output blocks
		if called_from_parallel and has_output:
			print("")

	return return_code
