"""
This module implements the `se renumber-endnotes` command.
"""

import argparse

import se
from se.se_epub import SeEpub


def renumber_endnotes() -> int:
	"""
	Entry point for `se renumber-endnotes`
	"""

	parser = argparse.ArgumentParser(description="Renumber all endnotes and noterefs sequentially from the beginning.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	return_code = 0

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
		except se.SeException as ex:
			se.print_error(ex)
			return_code = ex.code

		try:
			report = se_epub.generate_endnotes()  # returns a report on actions taken
			if args.verbose:
				print(report)
		except se.SeException as ex:
			se.print_error(ex)
			return_code = ex.code
		except FileNotFoundError:
			se.print_error("Couldn’t find `endnotes.xhtml`.")
			return_code = se.InvalidSeEbookException.code

	return return_code
