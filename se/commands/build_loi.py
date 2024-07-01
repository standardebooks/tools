"""
This module implements the `se build-loi` command.
"""

import argparse

import se
from se.se_epub import SeEpub

def build_loi(plain_output: bool) -> int:
	"""
	Entry point for `se build-loi`
	"""

	parser = argparse.ArgumentParser(description="Update the LoI file based on all <figure> elements that contain an <img>.")
	parser.add_argument("-s", "--stdout", action="store_true", help="print to stdout intead of writing to the LoI file")
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
			xhtml = se_epub.generate_loi()

			if args.stdout:
				print(xhtml)
			else:
				loi_path = se_epub.loi_path or (se_epub.content_path / "text/loi.xhtml")
				with open(loi_path, "w", encoding="utf-8") as file:
					file.write(xhtml)

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code
		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{se_epub.loi_path}]{se_epub.loi_path}[/][/].", plain_output=plain_output)
			return se.InvalidSeEbookException.code

	return 0
