"""
This module implements the `se build` command.
"""

import argparse
import os
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

import se
from se.se_epub import SeEpub

def build(plain_output: bool) -> int:
	"""
	Entry point for `se build`
	"""

	parser = argparse.ArgumentParser(description="Build compatible .epub and advanced .epub ebooks from a Standard Ebook source directory. Output is placed in the current directory, or the target directory with --output-dir.")
	parser.add_argument("-b", "--kobo", dest="build_kobo", action="store_true", help="also build a .kepub.epub file for Kobo")
	parser.add_argument("-c", "--check", action="store_true", help="use epubcheck to validate the compatible .epub file, and the Nu Validator (v.Nu) to validate XHTML5; if Ace is installed, also validate using Ace; if --kindle is also specified and epubcheck, v.Nu, or Ace fail, don’t create a Kindle file")
	parser.add_argument("-k", "--kindle", dest="build_kindle", action="store_true", help="also build an .azw3 file for Kindle")
	parser.add_argument("-o", "--output-dir", metavar="DIRECTORY", type=str, default="", help="a directory to place output files in; will be created if it doesn’t exist")
	parser.add_argument("-p", "--proof", dest="proof", action="store_true", help="insert additional CSS rules that are helpful for proofreading; output filenames will end in .proof")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("-y", "--check-only", action="store_true", help="run tests used by --check but don’t output any ebook files and exit after checking")
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

	if args.check_only and (args.check or args.build_kindle or args.build_kobo or args.proof or args.output_dir):
		se.print_error("The [bash]--check-only[/] option can’t be combined with any other flags except for [bash]--verbose[/].", plain_output=plain_output)
		return se.InvalidArgumentsException.code

	for directory in args.directories:
		directory = Path(directory).resolve()
		messages = []
		exception = None
		table_data = []
		has_output = False

		try:
			se_epub = SeEpub(directory)
			se_epub.build(args.check, args.check_only, args.build_kobo, args.build_kindle, Path(args.output_dir), args.proof)
		except se.BuildFailedException as ex:
			exception = ex
			messages = ex.messages
		except se.SeException as ex:
			se.print_error(ex, plain_output=plain_output)

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
			return_code = se.BuildFailedException.code

			if plain_output:
				for message in messages:
					# Replace color markup with `
					message.text = se.prep_output(message.text, True)

					message_filename = ""
					if message.filename:
						message_filename = message.filename.name

					console.print(f"{message.source}: {message.code} {message_filename}{message.location if message.location else ''} {message.text}")
			else:
				for message in messages:
					# Add hyperlinks around message filenames
					message_filename = ""
					if message.filename:
						message_filename = f"[link=file://{message.filename}]{message.filename.name}[/link]{message.location if message.location else ''}"

					table_data.append([message.source, message.code, message_filename, message.text])

					if message.submessages:
						for submessage in message.submessages:
							# Brackets don't need to be escaped in submessages if we instantiate them in Text()
							submessage_object = Text(submessage, style="dim")

							table_data.append([" ", " ", Text("→", justify="right"), submessage_object])

				table = Table(show_header=True, header_style="bold", show_lines=True, expand=True)
				table.add_column("Source", width=9, no_wrap=True)
				table.add_column("Code", no_wrap=True)
				table.add_column("File", no_wrap=True)
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
