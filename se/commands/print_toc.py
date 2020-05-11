"""
This module implements the `se print-toc` command.
"""

import argparse

import se
from se.se_epub import SeEpub


def print_toc() -> int:
	"""
	Entry point for `se print-toc`

	The meat of this function is broken out into the generate_toc.py module for readability
	and maintainability.
	"""

	parser = argparse.ArgumentParser(description="Build a table of contents for an SE source directory and print to stdout.")
	parser.add_argument("-i", "--in-place", action="store_true", help="overwrite the existing toc.xhtml file instead of printing to stdout")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	if not args.in_place and len(args.directories) > 1:
		se.print_error("Multiple directories are only allowed with the [bash]--in-place[/] option.")
		return se.InvalidArgumentsException.code

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

		try:
			if args.in_place:
				toc_path = se_epub.path / "src/epub/toc.xhtml"
				with open(toc_path, "r+", encoding="utf-8") as file:
					file.write(se_epub.generate_toc())
					file.truncate()
			else:
				print(se_epub.generate_toc())
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code
		except FileNotFoundError as ex:
			se.print_error(f"Couldn’t open file: [path][link=file://{toc_path}]{toc_path}[/][/].")
			return se.InvalidSeEbookException.code

	return 0
