"""
This module implements the `se word-count` command.
"""

import argparse

import se
import se.formatting


def word_count() -> int:
	"""
	Entry point for `se word-count`
	"""

	parser = argparse.ArgumentParser(description="Count the number of words in an XHTML file and optionally categorize by length. If multiple files are specified, show the total word count for all.")
	parser.add_argument("-c", "--categorize", action="store_true", help="include length categorization in output")
	parser.add_argument("-x", "--exclude-se-files", action="store_true", help="exclude some non-bodymatter files common to SE ebooks, like the ToC and colophon")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	total_word_count = 0

	excluded_filenames = []
	if args.exclude_se_files:
		excluded_filenames = se.IGNORED_FILENAMES

	for filename in se.get_target_filenames(args.targets, (".xhtml", ".html", ".htm"), excluded_filenames):
		if args.exclude_se_files and filename.name == "endnotes.xhtml":
			continue

		try:
			with open(filename, "r", encoding="utf-8") as file:
				try:
					total_word_count += se.formatting.get_word_count(file.read())
				except UnicodeDecodeError:
					se.print_error(f"File is not UTF-8: `{filename}`")
					return se.InvalidEncodingException.code

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: `{filename}`")
			return se.InvalidInputException.code

	if args.categorize:
		category = "se:short-story"
		if se.NOVELLA_MIN_WORD_COUNT <= total_word_count < se.NOVEL_MIN_WORD_COUNT:
			category = "se:novella"
		elif total_word_count >= se.NOVEL_MIN_WORD_COUNT:
			category = "se:novel"

	print(f"{total_word_count}\t{category if args.categorize else ''}")

	return 0
