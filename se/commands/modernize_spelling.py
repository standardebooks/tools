"""
This module implements the `se modernize-spelling` command.
"""

import argparse

from rich.console import Console

import se
import se.spelling


def modernize_spelling() -> int:
	"""
	Entry point for `se modernize-spelling`
	"""

	parser = argparse.ArgumentParser(description="Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling. For example, replace `ash-tray` with `ashtray`.")
	parser.add_argument("-n", "--no-hyphens", dest="modernize_hyphenation", action="store_false", help="don’t modernize hyphenation")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	return_code = 0
	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	for filename in se.get_target_filenames(args.targets, (".xhtml",)):
		if args.verbose:
			console.print(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", end="")

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				try:
					new_xhtml = se.spelling.modernize_spelling(xhtml)
					problem_spellings = se.spelling.detect_problem_spellings(xhtml)

					for problem_spelling in problem_spellings:
						console.print(f"{('[path][link=file://' + str(filename) + ']' + filename.name + '[/][/]') + ': ' if not args.verbose else ''}{problem_spelling}")

				except se.InvalidLanguageException as ex:
					se.print_error(f"{ex}{' File: [path][link=file://' + str(filename) + ']' + str(filename) + '[/][/]' if not args else ''}")
					return ex.code

				if args.modernize_hyphenation:
					new_xhtml = se.spelling.modernize_hyphenation(new_xhtml)

				if new_xhtml != xhtml:
					file.seek(0)
					file.write(new_xhtml)
					file.truncate()
		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].")
			return_code = se.InvalidInputException.code

		if args.verbose:
			console.print(" OK")

	return return_code
