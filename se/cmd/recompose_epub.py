"""
recompose-epub command
"""

import argparse

import se
from se.common import print_error
from se.se_epub import SeEpub


def cmd_recompose_epub() -> int:
	"""
	Entry point for `se recompose-epub`
	"""

	parser = argparse.ArgumentParser(description="Recompose a Standard Ebooks source directory into a single HTML5 file, and print to standard output.")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	try:
		se_epub = SeEpub(args.directory)
		print(se_epub.recompose())
	except se.SeException as ex:
		print_error(ex)
		return ex.code

	return 0
