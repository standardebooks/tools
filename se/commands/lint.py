"""
This module implements the `se lint` command.
"""

import argparse
import os
from pathlib import Path

import regex
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

import se
from se.se_epub import SeEpub

def lint(plain_output: bool) -> int:
	"""
	Entry point for `se lint`
	"""

	parser = argparse.ArgumentParser(description="Check for various Standard Ebooks style errors.")
	parser.add_argument("-a", "--allow", dest="allowed_messages", nargs="+", help="if an se-lint-ignore.xml file is present, allow these specific codes to be raised by lint")
	parser.add_argument("-s", "--skip-lint-ignore", action="store_true", help="ignore all rules in the se-lint-ignore.xml file")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	called_from_parallel = se.is_called_from_parallel(False)
	force_terminal = True if called_from_parallel else None # True will force colors, None will guess whether colors are enabled, False will disable colors
	first_output = True
	return_code = 0

	# Rich needs to know the terminal width in order to format tables.
	# If we're called from Parallel, there is no width because Parallel is not a terminal. Thus we must export $COLUMNS before
	# invoking Parallel, and then get that value here.
	console = Console(width=int(os.environ["COLUMNS"]) if called_from_parallel and "COLUMNS" in os.environ else None, highlight=False, theme=se.RICH_THEME, force_terminal=force_terminal) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	for directory in args.directories:
		directory = Path(directory).resolve()
		messages = []
		exception = None
		table_data = []
		has_output = False

		try:
			se_epub = SeEpub(directory)
			messages = se_epub.lint(args.skip_lint_ignore, args.allowed_messages)
		except se.SeException as ex:
			exception = ex
			if len(args.directories) > 1:
				return_code = se.LintFailedException.code
			else:
				return_code = ex.code

		# Print a separator newline if more than one table is printed
		if not first_output and (args.verbose or messages or exception):
			console.print("")
		elif first_output:
			first_output = False

		# Print the table header
		if ((len(args.directories) > 1 or called_from_parallel) and (messages or exception)) or args.verbose:
			has_output = True
			if plain_output:
				console.print(directory)
			else:
				console.print(f"[reverse][path][link=file://{directory}]{directory}[/][/][/reverse]")

		if exception:
			has_output = True
			se.print_error(exception, plain_output=plain_output)

		# Print the tables
		if messages:
			has_output = True
			return_code = se.LintFailedException.code

			if plain_output:
				for message in messages:
					label = "[Manual Review]"

					if message.message_type == se.MESSAGE_TYPE_ERROR:
						label = "[Error]"

					# Replace color markup with `
					message.text = se.prep_output(message.text, True)

					message_filename = ""
					if message.filename:
						message_filename = message.filename.name

					console.print(f"{message.code} {label} {message_filename} {message.text}")

					if message.submessages:
						for submessage in message.submessages:
							# Indent each line in case we have a multi-line submessage
							console.print(regex.sub(r"^", "\t", submessage, flags=regex.MULTILINE))
			else:
				for message in messages:
					alert = "[bright_yellow]Manual Review[/bright_yellow]"

					if message.message_type == se.MESSAGE_TYPE_ERROR:
						alert = "[bright_red]Error[/bright_red]"

					# Add hyperlinks around message filenames
					message_filename = ""
					if message.filename:
						message_filename = f"[link=file://{message.filename.resolve()}]{message.filename.name}[/link]"

					table_data.append([message.code, alert, message_filename, message.text])

					if message.submessages:
						for submessage in message.submessages:
							# Brackets don't need to be escaped in submessages if we instantiate them in Text()
							submessage_object = Text(submessage, style="dim")

							table_data.append([" ", " ", Text("→", justify="right"), submessage_object])

				table = Table(show_header=True, header_style="bold", show_lines=True, expand=True)
				table.add_column("Code", width=5, no_wrap=True)
				table.add_column("Severity", no_wrap=True)
				table.add_column("File", max_width=25, no_wrap=True)
				table.add_column("Message", ratio=10)

				for row in table_data:
					table.add_row(row[0], row[1], row[2], row[3])

				console.print(table)

		if args.verbose and not messages and not exception:
			if plain_output:
				console.print("OK")
			else:
				table = Table(show_header=False, box=box.SQUARE)
				table.add_column("", style="white on green4 bold")
				table.add_row("OK")
				console.print(table)

		# Print a newline if we're called from parallel and we just printed something, to
		# better visually separate output blocks
		if called_from_parallel and has_output:
			console.print("")

	return return_code
