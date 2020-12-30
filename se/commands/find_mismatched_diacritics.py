"""
This module implements the `se find-mismatched-diacritics` command.
"""

import argparse
import unicodedata

import regex

import se


def find_mismatched_diacritics() -> int:
	"""
	Entry point for `se find-mismatched-diacritics`
	"""

	parser = argparse.ArgumentParser(description="Find words with mismatched diacritics in a set of XHTML files. For example, `cafe` in one file and `café` in another.")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	return_code = 0
	accented_words = set()
	mismatches = {}
	target_filenames = se.get_target_filenames(args.targets, (".xhtml",))

	for filename in target_filenames:
		try:
			with open(filename, "r", encoding="utf-8") as file:
				xhtml = file.read()

				decomposed_xhtml = unicodedata.normalize("NFKD", xhtml)

				for decomposed_word in regex.findall(r"\b\w*\p{M}\w*\b", decomposed_xhtml):
					word = unicodedata.normalize("NFKC", decomposed_word)

					if len(word) > 2:
						accented_words.add(word.lower())

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].")
			return_code = se.InvalidInputException.code

	# Now iterate over the list and search files for unaccented versions of the words
	if accented_words:
		for filename in target_filenames:
			try:
				with open(filename, "r", encoding="utf-8") as file:
					xhtml = file.read()

					for accented_word in accented_words:
						plain_word = regex.sub(r"\p{M}", "", unicodedata.normalize("NFKD", accented_word))

						if regex.search(fr"\b{plain_word}\b", xhtml, regex.IGNORECASE) is not None:
							mismatches[accented_word] = plain_word

			except FileNotFoundError:
				se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].")
				return_code = se.InvalidInputException.code

	for accented_word, plain_word in sorted(mismatches.items()):
		print(f"{accented_word}\t{plain_word}")

	return return_code
