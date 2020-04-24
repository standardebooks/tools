"""
This module implements the `se lint` command.
"""

import argparse
import collections
import concurrent.futures
from pathlib import Path
import signal
import sys
from textwrap import wrap
from typing import List, Tuple

from colored import stylize, fg, bg, attr
import regex
import terminaltables

import se
from se.se_epub import SeEpub
from se.se_epub_lint import LintMessage

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

def _lint(directory: Path, skip_lint_ignore: bool) -> Tuple[str, List[LintMessage]]:
	se_epub = SeEpub(directory)
	return (str(se_epub.path), se_epub.lint(skip_lint_ignore))

def _keyboard_interrupt_handler(sigal_number, frame): # pylint: disable=unused-argument
	"""
	We need this function to "gracefully" catch keyboard interrupts in multiprocess mode.
	For some reason we can't bubble a KeyboardInterrupt exception up to main(), we have to hard exit here.
	Despite this handler, ctrl + c may still have to be pressed multiple times to register.
	This function *must* have two arguments, so disable the pylint warning.
	"""
	sys.exit(130) # See http://www.tldp.org/LDP/abs/html/exitcodes.html

def lint() -> int:
	"""
	Entry point for `se lint`
	"""

	parser = argparse.ArgumentParser(description="Check for various Standard Ebooks style errors.")
	parser.add_argument("-m", "--multiprocess", action="store_true", help="use multiprocessing to speed up execution when multiple ebooks are specified; ctrl + c doesn’t work nicely")
	parser.add_argument("-n", "--no-colors", dest="colors", action="store_false", help="do not use colored output")
	parser.add_argument("-p", "--plain", action="store_true", help="print plain text output, without tables or colors")
	parser.add_argument("-s", "--skip-lint-ignore", action="store_true", help="ignore rules in se-lint-ignore.xml file")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	first_output = True
	return_code = 0
	unsorted_messages = {}

	if args.multiprocess and len(args.directories) == 1:
		args.multiprocess = False

	if args.multiprocess:
		signal.signal(signal.SIGTERM, _keyboard_interrupt_handler)
		signal.signal(signal.SIGINT, _keyboard_interrupt_handler)

		futures = []
		with concurrent.futures.ProcessPoolExecutor() as executor:
			for directory in args.directories:
				futures.append(executor.submit(_lint, directory, args.skip_lint_ignore))

			for future in concurrent.futures.as_completed(futures):
				try:
					future_directory, future_messages = future.result()
					unsorted_messages[future_directory] = future_messages
				except se.SeException as ex:
					se.print_error(ex)
					first_output = False
					if len(args.directories) > 1:
						return_code = se.LintFailedException.code
					else:
						return_code = ex.code
	else:
		for directory in args.directories:
			try:
				se_epub = SeEpub(directory)
				unsorted_messages[str(se_epub.path)] = se_epub.lint(args.skip_lint_ignore)
			except se.SeException as ex:
				se.print_error(ex)
				first_output = False
				if len(args.directories) > 1:
					return_code = se.LintFailedException.code
				else:
					return_code = ex.code

	for directory, messages in collections.OrderedDict(sorted(unsorted_messages.items())).items():
		table_data = []

		# Print a separator newline if more than one table is printed
		if not first_output and (args.verbose or messages):
			print("")
		elif first_output:
			first_output = False

		# Print the table header
		if args.verbose or (messages and len(args.directories) > 1):
			if args.plain:
				print(directory)
			else:
				print(stylize(directory, attr("reverse")))

		# Print the tables
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
