"""
This module implements the `se prepare-release` command.
"""

import argparse
from pathlib import Path

import se
from se.se_help_formatter import SeHelpFormatter
from se.se_epub import SeEpub


def prepare_release(plain_output: bool) -> int:
	"""
	Entry point for `se prepare-release`.
	"""

	parser = argparse.ArgumentParser(description="Calculate work word count, insert release date if not yet set, and update modified date and revision number.", prog="[command]se[/] [subcommand]prepare-release[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-r", "--no-revision", dest="revision", action="store_false", help="Don’t increment the revision number.")
	parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity.")
	parser.add_argument("-w", "--no-word-count", dest="word_count", action="store_false", help="Don’t calculate word count.")
	parser.add_argument("directories", metavar="[path]DIRECTORY[/]", nargs="+", help="A Standard Ebooks source directory.")
	args = parser.parse_args()

	console =se.init_console()

	for directory in args.directories:
		directory = Path(directory).resolve()

		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{directory}]{directory}[/][/] ...", plain_output))

		try:
			se_epub = SeEpub(directory)

			if args.word_count:
				if args.verbose:
					console.print("\tUpdating word count and reading ease ...", end="")

				se_epub.update_word_count()
				se_epub.update_flesch_reading_ease()

				if args.verbose:
					console.print(" OK")

			if args.revision:
				if args.verbose:
					console.print("\tUpdating revision number ...", end="")

				se_epub.set_release_timestamp()

				if args.verbose:
					console.print(" OK")
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
