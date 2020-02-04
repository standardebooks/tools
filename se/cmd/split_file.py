"""
split-file command
"""

import argparse

import importlib_resources
import regex

from se.common import print_error, strip_bom


def cmd_split_file() -> int:
	"""
	Entry point for `se split-file`
	"""

	parser = argparse.ArgumentParser(description="Split an XHTML file into many files at all instances of <!--se:split-->, and include a header template for each file.")
	parser.add_argument("filename", metavar="FILE", help="an HTML/XHTML file")
	args = parser.parse_args()

	try:
		with open(args.filename, "r", encoding="utf-8") as file:
			xhtml = strip_bom(file.read())

	except FileNotFoundError:
		print_error(f"Not a file: {args.filename}")

	with importlib_resources.open_text("se.data.templates", "header.xhtml", encoding="utf-8") as file:
		header_xhtml = file.read()

	chapter_number = 1
	chapter_xhtml = ""

	# Remove leading split tags
	xhtml = regex.sub(r"^\s*<\!--se:split-->", "", xhtml)

	for line in xhtml.splitlines():
		if "<!--se:split-->" in line:
			prefix, suffix = line.split("<!--se:split-->")
			chapter_xhtml = chapter_xhtml + prefix
			_split_file_output_file(chapter_number, header_xhtml, chapter_xhtml)

			chapter_number = chapter_number + 1
			chapter_xhtml = suffix

		else:
			chapter_xhtml = chapter_xhtml + "\n" + line

	if chapter_xhtml and not chapter_xhtml.isspace():
		_split_file_output_file(chapter_number, header_xhtml, chapter_xhtml)

	return 0

def _split_file_output_file(chapter_number: int, header_xhtml: str, chapter_xhtml: str) -> None:
	"""
	Helper function for split_file() to write a file given the chapter number,
	header XHTML, and chapter body XHTML.
	"""

	with open("chapter-" + str(chapter_number) + ".xhtml", "w", encoding="utf-8") as file:
		file.write(header_xhtml.replace("NUMBER", str(chapter_number)) + "\n" + chapter_xhtml + "\n</section></body></html>")
		file.truncate()
