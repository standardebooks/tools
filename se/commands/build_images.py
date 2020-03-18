"""
This module implements the `se build-images` command.
"""

import argparse
import fnmatch
from pathlib import Path
import os

import se
from se.se_epub import SeEpub


def build_images() -> int:
	"""
	Entry point for `se build-images`
	"""

	parser = argparse.ArgumentParser(description="Build ebook covers and titlepages for a Standard Ebook source directory, and place the output in DIRECTORY/src/epub/images/.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	for directory in args.directories:
		directory = Path(directory)

		if args.verbose:
			print(f"Processing {directory} ...")

		directory = directory.resolve()

		se_epub = SeEpub(directory)

		try:
			if args.verbose:
				print("\tCleaning metadata ...", end="", flush=True)

			# Remove useless metadata from cover source files
			for root, _, filenames in os.walk(directory):
				for filename in fnmatch.filter(filenames, "cover.*"):
					se.images.remove_image_metadata(Path(root) / filename)

			if args.verbose:
				print(" OK")
				print("\tBuilding cover.svg ...", end="", flush=True)

			se_epub.generate_cover_svg()

			if args.verbose:
				print(" OK")
				print("\tBuilding titlepage.svg ...", end="", flush=True)

			se_epub.generate_titlepage_svg()

			if args.verbose:
				print(" OK")
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
