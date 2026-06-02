"""
This module implements the `se modernize-spelling` command.
"""

import argparse

import se
from se.se_help_formatter import SeHelpFormatter
import se.spelling


def modernize_spelling(plain_output: bool) -> int:
	"""
	Entry point for `se modernize-spelling`.
	"""

	parser = argparse.ArgumentParser(description="Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling. For example, replace [text]ash-tray[/] with [text]ashtray[/].", prog="[command]se[/] [subcommand]modernize-spelling[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-n", "--no-hyphens", dest="modernize_hyphenation", action="store_false", help="Don’t modernize hyphenation.")
	parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity.")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="An XHTML file, or a directory containing XHTML files.")
	args = parser.parse_args()

	return_code = 0
	console = se.init_console()

	for filename in se.get_target_filenames(args.targets, ".xhtml"):
		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", plain_output), end="")

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				try:
					new_xhtml = se.spelling.modernize_spelling(xhtml)
					problem_spellings = se.spelling.detect_problem_spellings(xhtml)

					for problem_spelling in problem_spellings:
						console.print(se.prep_output(f"{('[path][link=file://' + str(filename) + ']' + filename.name + '[/][/]') + ': ' if not args.verbose else ''}{problem_spelling}", plain_output))

				except se.InvalidLanguageException as ex:
					se.print_error(f"{ex} File: [path][link=file://{filename}]{filename}[/][/]", plain_output=plain_output)
					return ex.code

				if args.modernize_hyphenation:
					new_xhtml = se.spelling.modernize_hyphenation(new_xhtml)

				if new_xhtml != xhtml:
					file.seek(0)
					file.write(new_xhtml)
					file.truncate()
		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code

		if args.verbose:
			console.print(" OK")

	return return_code
