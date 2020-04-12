"""
This module implements the `se recompose-epub` command.
"""

import argparse

import se
from se.se_epub import SeEpub


def recompose_epub() -> int:
	"""
	Entry point for `se recompose-epub`
	"""

	parser = argparse.ArgumentParser(description="Recompose a Standard Ebooks source directory into a single (X?)HTML5 file, and print to standard output.")
	parser.add_argument("-o", "--output", metavar="FILE", type=str, default="", help="a file to write output to instead of printing to standard output")
	parser.add_argument("-x", "--xhtml", action="store_true", help="output XHTML instead of HTML5")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	try:
		se_epub = SeEpub(args.directory)
		recomposed_epub = se_epub.recompose(args.xhtml)

		if args.output:
			with open(args.output, "w", encoding="utf-8") as file:
				file.write(recomposed_epub)
				file.truncate()
		else:
			print(recomposed_epub)
	except se.SeException as ex:
		se.print_error(ex)
		return ex.code
	except Exception as ex:
		se.print_error("Couldn’t write to output file.")
		return se.InvalidFileException.code

	return 0
