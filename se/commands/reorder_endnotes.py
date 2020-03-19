"""
This module implements the `se reorder-endnotes` command.
"""

import argparse

import se
from se.se_epub import SeEpub


def reorder_endnotes() -> int:
	"""
	Entry point for `se reorder-endnotes`
	"""

	parser = argparse.ArgumentParser(description="Increment the specified endnote and all following endnotes by 1.")
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("-d", "--decrement", action="store_true", help="decrement the target endnote number and all following endnotes")
	group.add_argument("-i", "--increment", action="store_true", help="increment the target endnote number and all following endnotes")
	parser.add_argument("target_endnote_number", metavar="ENDNOTE-NUMBER", type=se.is_positive_integer, help="the endnote number to start reordering at")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	return_code = 0

	try:
		if args.increment:
			step = 1
		else:
			step = -1

		se_epub = SeEpub(args.directory)
		se_epub.reorder_endnotes(args.target_endnote_number, step)

	except se.SeException as ex:
		se.print_error(ex)
		return_code = ex.code

	return return_code
