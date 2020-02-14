"""
This module implements the `se split_file` command.
"""

import argparse

import importlib_resources
import regex

import se


def _split_file_output_file(filename_format_string: str, chapter_number: int, template_xhtml: str, chapter_xhtml: str) -> None:
	"""
	Helper function for split_file() to write a file given the chapter number,
	header XHTML, and chapter body XHTML.
	"""

	xhtml = template_xhtml.replace("NUMBER", str(chapter_number))
	xhtml = xhtml.replace("TEXT", chapter_xhtml)

	with open(filename_format_string.replace("%n", str(chapter_number)), "w", encoding="utf-8") as file:
		file.write(xhtml)
		file.truncate()

def split_file() -> int:
	"""
	Entry point for `se split-file`
	"""

	parser = argparse.ArgumentParser(description="Split an XHTML file into many files at all instances of <!--se:split-->, and include a header template for each file.")
	parser.add_argument("-s", "--start-at", metavar="INTEGER", type=se.is_positive_integer, default="1", help="start numbering chapters at this number, instead of at 1")
	parser.add_argument("-f", "--filename-format", metavar="STRING", type=str, default="chapter-%%n.xhtml", help="a format string for the output files; `%%n` is replaced with the current chapter number; defaults to `chapter-%%n.xhtml`")
	parser.add_argument("-t", "--template-file", metavar="FILE", type=str, default="", help="a file containing an XHTML template to use for each chapter; the string NUMBER is replaced by the chapter number, and the string TEXT is replaced by the chapter body")
	parser.add_argument("filename", metavar="FILE", help="an HTML/XHTML file")
	args = parser.parse_args()

	try:
		with open(args.filename, "r", encoding="utf-8") as file:
			xhtml = se.strip_bom(file.read())
	except FileNotFoundError:
		se.print_error(f"Not a file: {args.filename}")
		return se.InvalidFileException.code

	if args.template_file:
		try:
			with open(args.template_file, "r", encoding="utf-8") as file:
				template_xhtml = file.read()
		except FileNotFoundError:
			se.print_error(f"Not a file: {args.template_file}")
			return se.InvalidFileException.code
	else:
		with importlib_resources.open_text("se.data.templates", "chapter-template.xhtml", encoding="utf-8") as file:
			template_xhtml = file.read()

	chapter_xhtml = ""

	# Remove leading split tags
	xhtml = regex.sub(r"^\s*<\!--se:split-->", "", xhtml)

	for line in xhtml.splitlines():
		if "<!--se:split-->" in line:
			prefix, suffix = line.split("<!--se:split-->")
			chapter_xhtml = chapter_xhtml + prefix
			_split_file_output_file(args.filename_format, args.start_at, template_xhtml, chapter_xhtml)

			args.start_at = args.start_at + 1
			chapter_xhtml = suffix

		else:
			chapter_xhtml = chapter_xhtml + "\n" + line

	if chapter_xhtml and not chapter_xhtml.isspace():
		_split_file_output_file(args.filename_format, args.start_at, template_xhtml, chapter_xhtml)

	return 0
