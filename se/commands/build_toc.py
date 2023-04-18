"""
This module implements the `se build-toc` command.
"""

import argparse

import se
from se.se_epub import SeEpub


def build_toc(plain_output: bool) -> int:
	"""
	Entry point for `se build-toc`

	The meat of this function is broken out into the se_epub_generate_toc.py module for readability
	and maintainability.
	"""

	parser = argparse.ArgumentParser(description="Generate the table of contents for the ebook’s source directory and update the ToC file.")
	parser.add_argument("-s", "--stdout", action="store_true", help="print to stdout intead of writing to the ToC file")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	if args.stdout and len(args.directories) > 1:
		se.print_error("Multiple directories are only allowed without the [bash]--stdout[/] option.", plain_output=plain_output)
		return se.InvalidArgumentsException.code

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

		try:
			if args.stdout:
				print(se_epub.generate_toc())
			else:
				toc = se_epub.generate_toc()
				with open(se_epub.toc_path, "w", encoding="utf-8") as file:
					file.write(toc)

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code
		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{se_epub.toc_path}]{se_epub.toc_path}[/][/].", plain_output=plain_output)
			return se.InvalidSeEbookException.code

	return 0
