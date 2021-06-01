"""
This module implements the `se shift-endnotes` command.
"""

import argparse

import se
from se.se_epub import SeEpub


def shift_endnotes(plain_output: bool) -> int:
	"""
	Entry point for `se shift-endnotes`
	"""

	parser = argparse.ArgumentParser(description="Increment or decrement the specified endnote and all following endnotes by 1 or a specified amount.")
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("-d", "--decrement", action="store_true", help="decrement the target endnote number and all following endnotes")
	group.add_argument("-i", "--increment", action="store_true", help="increment the target endnote number and all following endnotes")
	parser.add_argument("-a", "--amount", metavar="NUMBER", dest="amount", default=1, type=se.is_positive_integer, help="the amount to increment or decrement by; defaults to 1")
	parser.add_argument("target_endnote_number", metavar="ENDNOTE-NUMBER", type=se.is_positive_integer, help="the endnote number to start shifting at")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	return_code = 0

	try:
		if args.increment:
			step = args.amount
		else:
			step = args.amount * -1

		se_epub = SeEpub(args.directory)
		se_epub.shift_endnotes(args.target_endnote_number, step)

	except se.SeException as ex:
		se.print_error(ex, plain_output=plain_output)
		return_code = ex.code

	return return_code
