"""
This module implements the `se extract_ebook` command.
"""

import argparse
import sys
import zipfile
from io import BytesIO, TextIOWrapper
from pathlib import Path

import magic

import se
from se.vendor.kindleunpack import kindleunpack


def extract_ebook() -> int:
	"""
	Entry point for `se extract-ebook`
	"""

	parser = argparse.ArgumentParser(description="Extract an epub, mobi, or azw3 ebook into ./FILENAME.extracted/ or a target directory.")
	parser.add_argument("-o", "--output-dir", type=str, help="a target directory to extract into")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an epub, mobi, or azw3 file")
	args = parser.parse_args()

	for target in args.targets:
		target = Path(target).resolve()

		if args.verbose:
			print(f"Processing {target} ...", end="", flush=True)

		if args.output_dir is None:
			extracted_path = Path(target.name + ".extracted")
		else:
			extracted_path = Path(args.output_dir)

		if extracted_path.exists():
			se.print_error(f"Directory already exists: {extracted_path}")
			return se.FileExistsException.code

		mime_type = magic.from_file(str(target))

		if "Mobipocket E-book" in mime_type:
			# kindleunpack uses print() so just capture that output here
			old_stdout = sys.stdout
			sys.stdout = TextIOWrapper(BytesIO(), sys.stdout.encoding)

			kindleunpack.unpackBook(str(target), str(extracted_path))

			# Restore stdout
			sys.stdout.close()
			sys.stdout = old_stdout
		elif "EPUB document" in mime_type:
			with zipfile.ZipFile(target, "r") as file:
				file.extractall(extracted_path)
		else:
			se.print_error(f"Couldn’t understand file type: {mime_type}")
			return se.InvalidFileException.code

		if args.verbose:
			print(" OK")

	return 0
