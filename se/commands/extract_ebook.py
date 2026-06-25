"""
This module implements the `se extract-ebook` command.
"""

import argparse
import datetime
from os import path
import shutil
import sys
import tempfile
import zipfile
from io import BytesIO, TextIOWrapper
from pathlib import Path
from xml.etree import ElementTree

import se
from se.se_help_formatter import SeHelpFormatter
from se.vendor.kindleunpack import kindleunpack

_FALLBACK_ZIP_MTIME: tuple[int, int, int, int, int, int] = (1980, 1, 1, 0, 0, 0)

def _is_epub(file_bytes: bytes) -> bool:
	"""
	Decide if a file is an epub file.

	From <https://github.com/h2non/filetype.py> (MIT license).
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

	From ./se/vendor/kindleunpack/mobi_sectioner.py lines 49-53.
	"""

	return file_bytes[:78][0x3C:0x3C+8] in (b"BOOKMOBI", b"TEXtREAd")

def _get_publication_mtime(content_opf_path: Path) -> tuple[int, int, int, int, int, int]:
	"""
	Get the publication date from an OPF file and convert it to an mtime tuple suitable for use in the zip format.
	"""

	dom = ElementTree.parse(content_opf_path)
	namespaces = {
		"dc": "http://purl.org/dc/elements/1.1/",
		"opf": "http://www.idpf.org/2007/opf"
	}
	publication_date_node = dom.find(".//dc:date[@opf:event='publication']", namespaces)

	if publication_date_node is None or publication_date_node.text is None:
		return _FALLBACK_ZIP_MTIME

	publication_datetime = datetime.datetime.fromisoformat(publication_date_node.text.strip())

	if publication_datetime.tzinfo is not None:
		publication_datetime = publication_datetime.astimezone(datetime.timezone.utc).replace(tzinfo=None)

	# Zip files store seconds at two-second precision.
	second = publication_datetime.second - (publication_datetime.second % 2)

	return (publication_datetime.year, publication_datetime.month, publication_datetime.day, publication_datetime.hour, publication_datetime.minute, second)

def _normalize_zip_mtimes(epub_path: Path, mtime: tuple[int, int, int, int, int, int]) -> None:
	"""
	Rewrite a zip file so that each entry has the given modification time.
	"""

	with tempfile.TemporaryDirectory() as temp_directory:
		temp_epub_path = Path(temp_directory) / epub_path.name

		with zipfile.ZipFile(epub_path, "r") as input_zip:
			with zipfile.ZipFile(temp_epub_path, "w") as output_zip:
				for input_info in input_zip.infolist():
					output_info = zipfile.ZipInfo(input_info.filename, mtime)
					output_info.comment = input_info.comment
					output_info.compress_type = input_info.compress_type
					output_info.create_system = input_info.create_system
					output_info.external_attr = input_info.external_attr
					output_info.internal_attr = input_info.internal_attr

					output_zip.writestr(output_info, input_zip.read(input_info.filename))

		shutil.move(temp_epub_path, epub_path)

def extract_ebook(plain_output: bool) -> int:
	"""
	Entry point for `se extract-ebook`.
	"""

	parser = argparse.ArgumentParser(description="Extract an [path].epub[/], [path].mobi[/], or [path].azw3[/] ebook into [path]./FILENAME.extracted/[/] or a target directory.", prog="[command]se[/] [subcommand]extract-ebook[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-o", "--output-dir", metavar="[path]DIRECTORY[/]", type=str, help="A target directory to extract into.")
	parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity.")
	parser.add_argument("targets", metavar="[path]TARGET[/]", nargs="+", help="An [path].epub[/], [path].mobi[/], or [path].azw3[/] file.")
	args = parser.parse_args()

	console = se.init_console()

	if args.output_dir and len(args.targets) > 1:
		se.print_error("The [flag]--output-dir[/] option can’t be used when more than one ebook target is specified.", plain_output=plain_output)
		return se.InvalidArgumentsException.code

	for target in args.targets:
		target = Path(target).resolve()

		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{target}]{target}[/][/] ...", plain_output), end="")

		if not path.isfile(target):
			se.print_error(f"Not a file: [path][link=file://{target}]{target}[/][/].", plain_output=plain_output)
			return se.InvalidInputException.code

		if args.output_dir is None:
			extracted_path = Path(target.name + ".extracted")
		else:
			extracted_path = Path(args.output_dir)

		if extracted_path.exists():
			se.print_error(f"Directory already exists: [path][link=file://{extracted_path}]{extracted_path}[/][/].", plain_output=plain_output)
			return se.FileExistsException.code

		with open(target, "rb") as binary_file:
			file_bytes = binary_file.read()

		if _is_mobi(file_bytes):
			# `kindleunpack` uses `print()` so just capture that output here.
			old_stdout = sys.stdout
			sys.stdout = TextIOWrapper(BytesIO(), sys.stdout.encoding)

			try:
				kindleunpack.unpackBook(str(target), str(extracted_path))
			finally:
				# Restore `stdout`.
				sys.stdout.close()
				sys.stdout = old_stdout

			# KindleUnpack re-generates an epub file inside the output folder. In doing this it changes the epub's file mtime, which makes the output non-reproducible.
			# Here, we explicitly set the mtime of the internal epub file to the publication date in `content.opf`, thus making the output reproducible.
			publication_mtime = _get_publication_mtime(extracted_path / "mobi8" / "OEBPS" / "content.opf")

			for epub_path in sorted((extracted_path / "mobi8").glob("*.epub")):
				_normalize_zip_mtimes(epub_path, publication_mtime)
		elif _is_epub(file_bytes):
			with zipfile.ZipFile(target, "r") as file:
				file.extractall(extracted_path)
		else:
			se.print_error(f"File doesn’t look like an epub, mobi, or azw3: [path][link=file://{target}]{target}[/][/].", plain_output=plain_output)
			return se.InvalidFileException.code

		if args.verbose:
			console.print(" OK")

	return 0
