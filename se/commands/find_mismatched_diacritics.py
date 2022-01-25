"""
This module implements the `se find-mismatched-diacritics` command.
"""

import argparse
from typing import Dict, Tuple
import urllib
import unicodedata

import regex
from rich import box
from rich.console import Console
from rich.table import Table

import se


def find_mismatched_diacritics(plain_output: bool) -> int:
	"""
	Entry point for `se find-mismatched-diacritics`
	"""

	parser = argparse.ArgumentParser(description="Find words with mismatched diacritics in a set of XHTML files. For example, `cafe` in one file and `café` in another.")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME) # Syntax highlighting will do weird things when printing paths
	return_code = 0
	accented_words: Dict[str, int] = {} # key: word; value: count
	mismatches: Dict[str, Dict[str, Tuple[int, int]]] = {} # key: base word; value: dict with key: plain word; value: (base count, plain count)
	target_filenames = se.get_target_filenames(args.targets, ".xhtml")
	files_xhtml = []

	# Read files and cache for later
	for filename in target_filenames:
		try:
			with open(filename, "r", encoding="utf-8") as file:
				xhtml = file.read()
				dom = se.easy_xml.EasyXmlTree(xhtml)

				# Save any `alt` and `title` attributes because we may be interested in their contents
				for node in dom.xpath("//*[@alt or @title]"):
					for _, value in node.attrs.items():
						xhtml = xhtml + f" {value} "

				# If we're in the colophon, remove the SE link because the author's name might have diacritics
				if dom.xpath("/html/body//section[contains(@epub:type, 'colophon')]"):
					xhtml = regex.sub(r"<a href=\"https://standardebooks\.org.+?</a>", "", xhtml)

				# Strip tags
				xhtml = regex.sub(r"<[^>]+?>", " ", xhtml)

				files_xhtml.append(xhtml)

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code

		except se.SeException as ex:
			se.print_error(str(ex) + f" File: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = ex.code

	# Create a list of accented words
	for xhtml in files_xhtml:
		decomposed_xhtml = unicodedata.normalize("NFKD", xhtml)

		for decomposed_word in regex.findall(r"\b\w*\p{M}\w*\b", decomposed_xhtml):
			word = unicodedata.normalize("NFKC", decomposed_word).lower()

			if len(word) > 2:
				if word in accented_words:
					accented_words[word] = accented_words[word] + 1
				else:
					accented_words[word] = 1

	# Now iterate over the list and search files for unaccented versions of the words
	if accented_words:
		for xhtml in files_xhtml:
			for accented_word, count in accented_words.items():
				plain_word = regex.sub(r"\p{M}", "", unicodedata.normalize("NFKD", accented_word))

				matches = regex.findall(fr"\b{plain_word}\b", xhtml, flags=regex.IGNORECASE)

				if matches:
					if accented_word in mismatches:
						if plain_word in mismatches[accented_word]:
							mismatches[accented_word][plain_word] = (count, mismatches[accented_word][plain_word][1] + len(matches))
						else:
							mismatches[accented_word][plain_word] = (count, len(matches))

					else:
						mismatches[accented_word] = {}
						mismatches[accented_word][plain_word] = (count, len(matches))

	# Search for some exceptions
	filtered_mismatches = {}
	for accented_word, child in mismatches.items():
		keep_word = True
		if accented_word == "hôtel":
			keep_word = False
			for xhtml in files_xhtml:
				# Ignore cases of `maitre d'hôtel`, `hôtel du nord`, `hôtel d’nord`, `hôtel des baines`
				if regex.search(r"(?<!d’)hôtel(?!\sd[ue]\b)(?!\sd’)(?!\sdes\b)", xhtml, flags=regex.IGNORECASE):
					keep_word = True
					break

		if keep_word:
			filtered_mismatches[accented_word] = child

	# Sort and prepare the output
	mismatches = filtered_mismatches

	lines = []

	for accented_word, child in mismatches.items():
		for plain_word, counts in child.items():
			lines.append((accented_word, counts[0], plain_word, counts[1]))

	lines.sort()

	if lines:
		if plain_output:
			for accented_word, accented_word_count, plain_word, plain_word_count in lines:
				console.print(f"{accented_word} ({accented_word_count})\t{plain_word} ({plain_word_count})")

		else:
			table = Table(show_header=False, show_lines=True, box=box.HORIZONTALS)
			table.add_column("Dashed word")
			table.add_column("Count", style="dim", no_wrap=True)
			table.add_column("Plain word")
			table.add_column("Count", style="dim", no_wrap=True)

			for accented_word, accented_word_count, plain_word, plain_word_count in lines:
				table.add_row(f"[link=https://www.merriam-webster.com/dictionary/{urllib.parse.quote(accented_word)}]{accented_word}[/]", f"({accented_word_count})", f"[link=https://www.merriam-webster.com/dictionary/{urllib.parse.quote(plain_word)}]{plain_word}[/]", f"({plain_word_count})")

			console.print(table)

	return return_code
