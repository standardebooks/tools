"""
This module implements the `se build` command.
"""

import argparse
from pathlib import Path

import se
from se.se_epub import SeEpub


def build() -> int:
	"""
	Entry point for `se build`
	"""

	parser = argparse.ArgumentParser(description="Build compatible .epub and pure .epub3 ebooks from a Standard Ebook source directory. Output is placed in the current directory, or the target directory with --output-dir.")
	parser.add_argument("-b", "--kobo", dest="build_kobo", action="store_true", help="also build a .kepub.epub file for Kobo")
	parser.add_argument("-c", "--check", action="store_true", help="use epubcheck to validate the compatible .epub file; if --kindle is also specified and epubcheck fails, don’t create a Kindle file")
	parser.add_argument("-k", "--kindle", dest="build_kindle", action="store_true", help="also build an .azw3 file for Kindle")
	parser.add_argument("-o", "--output-dir", metavar="DIRECTORY", type=str, default="", help="a directory to place output files in; will be created if it doesn’t exist")
	parser.add_argument("-p", "--proof", action="store_true", help="insert additional CSS rules that are helpful for proofreading; output filenames will end in .proof")
	parser.add_argument("-t", "--covers", dest="build_covers", action="store_true", help="output the cover and a cover thumbnail; can only be used when there is a single build target")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	if args.build_covers and len(args.directories) > 1:
		se.print_error("`--covers` option specified, but more than one build target specified.")
		return se.InvalidArgumentsException.code

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
			se_epub.build(args.check, args.build_kobo, args.build_kindle, Path(args.output_dir), args.proof, args.build_covers, args.verbose)
		except se.SeException as ex:
			se.print_error(ex, args.verbose)
			return ex.code

	return 0
