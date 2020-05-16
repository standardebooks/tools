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
			found_endnote_count, changed_endnote_count = se_epub.generate_endnotes()
			if args.verbose:
				print(f"Found {found_endnote_count} endnote{'s' if found_endnote_count != 1 else ''} and changed {changed_endnote_count} endnote{'s' if changed_endnote_count != 1 else ''}.")
		except se.SeException as ex:
			se.print_error(ex)
			return_code = ex.code
		except FileNotFoundError:
			se.print_error("Couldn’t find [path]endnotes.xhtml[/].")
			return_code = se.InvalidSeEbookException.code

	return return_code
