"""
This module implements the `se word-count` command.
"""

import argparse
import chardet

import regex

import se
import se.formatting


NOVELLA_MIN_WORD_COUNT = 17500
NOVEL_MIN_WORD_COUNT = 40000

def word_count(plain_output: bool) -> int:
	"""
	Entry point for `se word-count`
	"""

	parser = argparse.ArgumentParser(description="Count the number of words in an XHTML file and optionally categorize by length. If multiple files are specified, show the total word count for all.")
	parser.add_argument("-c", "--categorize", action="store_true", help="include length categorization in output")
	parser.add_argument("-p", "--ignore-pg-boilerplate", action="store_true", help="attempt to ignore Project Gutenberg boilerplate headers and footers before counting")
	parser.add_argument("-x", "--exclude-se-files", action="store_true", help="exclude some non-bodymatter files common to S.E. ebooks, like the ToC and colophon")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	total_word_count = 0

	excluded_files = []
	if args.exclude_se_files:
		excluded_files = ["colophon", "titlepage", "imprint", "copyright-page", "halftitlepage", "toc", "loi", "endnotes"]

	for filename in se.get_target_filenames(args.targets, (".xhtml", ".html", ".htm")):
		try:
			with open(filename, "r", encoding="utf-8") as file:
				try:
					xhtml = file.read()
				except UnicodeDecodeError:
					# The file we're passed isn't utf-8. Try to convert it here.
					try:
						with open(filename, "rb") as binary_file:
							binary_xhtml = binary_file.read()
							xhtml = binary_xhtml.decode(chardet.detect(binary_xhtml)["encoding"] or "")
					except UnicodeDecodeError:
						se.print_error(f"File is not UTF-8: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
						return se.InvalidEncodingException.code

			# Remove HTML entities
			xhtml = regex.sub(r"&[^;\s\b]+?;", " ", xhtml)

			is_ignored, dom = se.get_dom_if_not_ignored(xhtml, excluded_files)

			if not is_ignored:
				# Try to remove PG header/footers
				if args.ignore_pg_boilerplate:
					if dom:
						for node in dom.xpath("//span[contains(@class, 'pagenum')]"):
							node.remove()

						for node in dom.xpath("//*[(name()='pre' or name()='div' or name()='p') and re:test(., 'Project Gutenberg', 'i')]"):
							node.remove()

						xhtml = dom.to_string()

					else:
						# We couldn't generate a dom, fall back to regex replacements
						xhtml = regex.sub(r"<(pre|div|p)[^>]*?>[^<]*Project Gutenberg[^<]+?</\1>", "", xhtml, flags=regex.IGNORECASE|regex.DOTALL)
						xhtml = regex.sub(r"<span class=\"pagenum\">.+?</span>", "", xhtml, flags=regex.IGNORECASE|regex.DOTALL)

				total_word_count += se.formatting.get_word_count(xhtml)

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return se.InvalidInputException.code

	if args.categorize:
		category = "se:short-story"
		if NOVELLA_MIN_WORD_COUNT <= total_word_count < NOVEL_MIN_WORD_COUNT:
			category = "se:novella"
		elif total_word_count >= NOVEL_MIN_WORD_COUNT:
			category = "se:novel"

	print(f"{total_word_count}\t{category if args.categorize else ''}")

	return 0
