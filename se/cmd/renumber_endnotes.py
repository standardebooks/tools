"""
renumber-endnotes command
"""

import argparse

import se
from se.common import print_error
from se.se_epub import SeEpub


def cmd_renumber_endnotes() -> int:
	"""
	Entry point for `se renumber-endnotes`
	"""

	parser = argparse.ArgumentParser(description="Renumber all endnotes and noterefs sequentially from the beginning.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
		except se.SeException as ex:
			print_error(ex)
			return ex.code

		try:
			report = se_epub.generate_endnotes()  # returns a report on actions taken
			if args.verbose:
				print(report)
		except se.SeException as ex:
			print_error(ex)
			return ex.code
		except FileNotFoundError:
			print_error("Couldn’t find endnotes.xhtml file.")
			return se.InvalidSeEbookException.code

	return 0
