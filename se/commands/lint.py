"""
This module implements the `se lint` command.
"""

import argparse
from pathlib import Path

import regex
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

import se
from se.se_epub import SeEpub

def lint() -> int:
	"""
	Entry point for `se lint`
	"""

	parser = argparse.ArgumentParser(description="Check for various Standard Ebooks style errors.")
	parser.add_argument("-n", "--no-colors", dest="colors", action="store_false", help="don’t use color or hyperlinks in output")
	parser.add_argument("-p", "--plain", action="store_true", help="print plain text output, without tables or colors")
	parser.add_argument("-s", "--skip-lint-ignore", action="store_true", help="ignore rules in se-lint-ignore.xml file")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	called_from_parallel = se.is_called_from_parallel()
	first_output = True
	return_code = 0
	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=called_from_parallel) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	for directory in args.directories:
		directory = Path(directory).resolve()
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
			console.print("")
		elif first_output:
			first_output = False

		# Print the table header
		if ((len(args.directories) > 1 or called_from_parallel) and (messages or exception)) or args.verbose:
			has_output = True
			if args.plain:
				console.print(directory)
			else:
				console.print(f"[reverse]{directory}[/reverse]")

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

					# Replace color markup with `
					message.text = regex.sub(r"\[(?:/|xhtml|xml|val|attr|val|class|path|url|text|bash|link)(?:=[^\]]*?)*\]", "`", message.text)
					message.text = regex.sub(r"`+", "`", message.text)

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
					alert = "Manual Review"

					if message.message_type == se.MESSAGE_TYPE_ERROR:
						alert = "Error"

					message_text = message.text

					if args.colors:
						if message.message_type == se.MESSAGE_TYPE_ERROR:
							alert = f"[bright_red]{alert}[/bright_red]"
						else:
							alert = f"[bright_yellow]{alert}[/bright_yellow]"

						# Add hyperlinks around message filenames
						message_filename = ""
						if message.filename:
							message_filename = f"[link=file://{message.filename.resolve()}]{message.filename.name}[/link]"
					else:
						# Replace color markup with `
						message_text = regex.sub(r"\[(?:/|xhtml|xml|val|attr|val|class|path|url|text|bash|link)(?:=[^\]]*?)*\]", "`", message_text)
						message_text = regex.sub(r"`+", "`", message_text)
						message_filename = ""
						if message.filename:
							message_filename = message.filename.name

					table_data.append([message.code, alert, message_filename, message_text])

					if message.submessages:
						for submessage in message.submessages:
							# Brackets don't need to be escaped in submessages if we instantiate them in Text()
							if args.colors:
								submessage_object = Text(submessage, style="dim")
							else:
								submessage_object = Text(submessage)

							table_data.append([" ", " ", Text("→", justify="right"), submessage_object])

				table = Table(show_header=True, header_style="bold", show_lines=True)
				table.add_column("Code", width=5, no_wrap=True)
				table.add_column("Severity", no_wrap=True)
				table.add_column("File", no_wrap=True)
				table.add_column("Message")

				for row in table_data:
					table.add_row(row[0], row[1], row[2], row[3])

				console.print(table)

		if args.verbose and not messages and not exception:
			if args.plain:
				console.print("OK")
			else:
				table = Table(show_header=False, box=box.SQUARE)
				table.add_column("", style="white on green4 bold" if args.colors else None)
				table.add_row("OK")
				console.print(table)

		# Print a newline if we're called from parallel and we just printed something, to
		# better visually separate output blocks
		if called_from_parallel and has_output:
			console.print("")

	return return_code
