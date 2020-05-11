"""
This module implements the `se print-manifest` command.
"""

import argparse

import regex

import se
from se.se_epub import SeEpub


def print_manifest() -> int:
	"""
	Entry point for `se print-manifest`
	"""

	parser = argparse.ArgumentParser(description="Print the <manifest> element for the given Standard Ebooks source directory to standard output, for use in that directory’s content.opf.")
	parser.add_argument("-i", "--in-place", action="store_true", help="overwrite the <manifest> element in content.opf instead of printing to stdout")
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

		if args.in_place:
			se_epub.metadata_xml = regex.sub(r"\s*<manifest>.+?</manifest>", "\n\t" + "\n\t".join(se_epub.generate_manifest().splitlines()), se_epub.metadata_xml, flags=regex.DOTALL)

			with open(se_epub.metadata_file_path, "r+", encoding="utf-8") as file:
				file.write(se_epub.metadata_xml)
				file.truncate()
		else:
			print(se_epub.generate_manifest())

	return 0
