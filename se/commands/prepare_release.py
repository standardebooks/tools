"""
This module implements the `se prepare-release` command.
"""

import argparse
from pathlib import Path

import se
from se.se_epub import SeEpub


def prepare_release() -> int:
	"""
	Entry point for `se prepare-release`
	"""

	parser = argparse.ArgumentParser(description="Calculate work word count, insert release date if not yet set, and update modified date and revision number.")
	parser.add_argument("-n", "--no-word-count", dest="word_count", action="store_false", help="don’t calculate word count")
	parser.add_argument("-r", "--no-revision", dest="revision", action="store_false", help="don’t increment the revision number")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	for directory in args.directories:
		directory = Path(directory).resolve()

		if args.verbose:
			print(f"Processing {directory} ...")

		try:
			se_epub = SeEpub(directory)

			if args.word_count:
				if args.verbose:
					print("\tUpdating word count and reading ease ...", end="", flush=True)

				se_epub.update_word_count()
				se_epub.update_flesch_reading_ease()

				if args.verbose:
					print(" OK")

			if args.revision:
				if args.verbose:
					print("\tUpdating revision number ...", end="", flush=True)

				se_epub.set_release_timestamp()

				if args.verbose:
					print(" OK")
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
