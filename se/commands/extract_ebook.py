"""
This module implements the `se extract-ebook` command.
"""

import argparse
from os import path
import sys
import zipfile
from io import BytesIO, TextIOWrapper
from pathlib import Path

from rich.console import Console

import se
from se.vendor.kindleunpack import kindleunpack


def _is_epub(file_bytes: bytes) -> bool:
	"""
	Decide if a file is an epub file.
	From https://github.com/h2non/filetype.py (MIT license)
	"""

	return (len(file_bytes) > 57 and
		file_bytes[0] == 0x50 and file_bytes[1] == 0x4B and
		file_bytes[2] == 0x3 and file_bytes[3] == 0x4 and
		file_bytes[30] == 0x6D and file_bytes[31] == 0x69 and
		file_bytes[32] == 0x6D and file_bytes[33] == 0x65 and
		file_bytes[34] == 0x74 and file_bytes[35] == 0x79 and
		file_bytes[36] == 0x70 and file_bytes[37] == 0x65 and
		file_bytes[38] == 0x61 and file_bytes[39] == 0x70 and
		file_bytes[40] == 0x70 and file_bytes[41] == 0x6C and
		file_bytes[42] == 0x69 and file_bytes[43] == 0x63 and
		file_bytes[44] == 0x61 and file_bytes[45] == 0x74 and
		file_bytes[46] == 0x69 and file_bytes[47] == 0x6F and
		file_bytes[48] == 0x6E and file_bytes[49] == 0x2F and
		file_bytes[50] == 0x65 and file_bytes[51] == 0x70 and
		file_bytes[52] == 0x75 and file_bytes[53] == 0x62 and
		file_bytes[54] == 0x2B and file_bytes[55] == 0x7A and
		file_bytes[56] == 0x69 and file_bytes[57] == 0x70)

def _is_mobi(file_bytes: bytes) -> bool:
	"""
	Decide if a file is a MOBI/AZW3 file.
	From ./se/vendor/kindleunpack/mobi_sectioner.py lines 49-53
	"""

	return file_bytes[:78][0x3C:0x3C+8] in (b"BOOKMOBI", b"TEXtREAd")

def extract_ebook() -> int:
	"""
	Entry point for `se extract-ebook`
	"""

	parser = argparse.ArgumentParser(description="Extract an epub, mobi, or azw3 ebook into ./FILENAME.extracted/ or a target directory.")
	parser.add_argument("-o", "--output-dir", type=str, help="a target directory to extract into")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an epub, mobi, or azw3 file")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	for target in args.targets:
		target = Path(target).resolve()

		if args.verbose:
			console.print(f"Processing [path][link=file://{target}]{target}[/][/] ...", end="")

		if not path.isfile(target):
			se.print_error(f"Not a file: [path][link=file://{target}]{target}[/][/].")
			return se.InvalidInputException.code

		if args.output_dir is None:
			extracted_path = Path(target.name + ".extracted")
		else:
			extracted_path = Path(args.output_dir)

		if extracted_path.exists():
			se.print_error(f"Directory already exists: [path][link=file://{extracted_path}]{extracted_path}[/][/].")
			return se.FileExistsException.code

		with open(target, "rb") as binary_file:
			file_bytes = binary_file.read()

		if _is_mobi(file_bytes):
			# kindleunpack uses print() so just capture that output here
			old_stdout = sys.stdout
			sys.stdout = TextIOWrapper(BytesIO(), sys.stdout.encoding)

			kindleunpack.unpackBook(str(target), str(extracted_path))

			# Restore stdout
			sys.stdout.close()
			sys.stdout = old_stdout
		elif _is_epub(file_bytes):
			with zipfile.ZipFile(target, "r") as file:
				file.extractall(extracted_path)
		else:
			se.print_error("File doesn’t look like an epub, mobi, or azw3 file.")
			return se.InvalidFileException.code

		if args.verbose:
			console.print(" OK")

	return 0
