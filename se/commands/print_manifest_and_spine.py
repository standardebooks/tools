"""
This module implements the `se print_manifest_and_spine` command.
"""

import argparse

import regex

import se
from se.se_epub import SeEpub


def print_manifest_and_spine() -> int:
	"""
	Entry point for `se print-manifest-and-spine`
	"""

	parser = argparse.ArgumentParser(description="Print <manifest> and <spine> tags to standard output for the given Standard Ebooks source directory, for use in that directory’s content.opf.")
	parser.add_argument("-m", "--manifest", action="store_true", help="only print the manifest")
	parser.add_argument("-s", "--spine", action="store_true", help="only print the spine")
	parser.add_argument("-i", "--in-place", action="store_true", help="overwrite the <manifest> or <spine> tags in content.opf instead of printing to stdout")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	if not args.in_place and len(args.directories) > 1:
		se.print_error("Multiple directories are only allowed with the --in-place option.")
		return se.InvalidInputException.code

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

		if not args.spine and not args.manifest:
			args.spine = True
			args.manifest = True

		if args.in_place:
			if args.spine:
				se_epub.metadata_xhtml = regex.sub(r"\s*<spine>.+?</spine>", "\n\t" + "\n\t".join(se_epub.generate_spine().splitlines()), se_epub.metadata_xhtml, flags=regex.DOTALL)

			if args.manifest:
				se_epub.metadata_xhtml = regex.sub(r"\s*<manifest>.+?</manifest>", "\n\t" + "\n\t".join(se_epub.generate_manifest().splitlines()), se_epub.metadata_xhtml, flags=regex.DOTALL)

			with open(se_epub.metadata_file_path, "r+", encoding="utf-8") as file:
				file.write(se_epub.metadata_xhtml)
				file.truncate()
		else:
			if args.manifest:
				print(se_epub.generate_manifest())

			if args.spine:
				print(se_epub.generate_spine())

	return 0
