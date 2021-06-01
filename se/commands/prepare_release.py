"""
This module implements the `se prepare-release` command.
"""

import argparse
from pathlib import Path

from rich.console import Console

import se
from se.se_epub import SeEpub


def prepare_release(plain_output: bool) -> int:
	"""
	Entry point for `se prepare-release`
	"""

	parser = argparse.ArgumentParser(description="Calculate work word count, insert release date if not yet set, and update modified date and revision number.")
	parser.add_argument("-w", "--no-word-count", dest="word_count", action="store_false", help="don’t calculate word count")
	parser.add_argument("-r", "--no-revision", dest="revision", action="store_false", help="don’t increment the revision number")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

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
			se.print_error(ex, plain_output=plain_output)
			return ex.code

	return 0
