"""
This module implements the `se semanticate` command.
"""

import argparse

from rich.console import Console

import se
import se.formatting


def semanticate() -> int:
	"""
	Entry point for `se semanticate`
	"""

	parser = argparse.ArgumentParser(description="Automatically add semantics to Standard Ebooks source directories.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel
	return_code = 0

	for filename in se.get_target_filenames(args.targets, (".xhtml",)):
		if args.verbose:
			console.print(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", end="")

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()
				processed_xhtml = se.formatting.semanticate(xhtml)

				if processed_xhtml != xhtml:
					file.seek(0)
					file.write(processed_xhtml)
					file.truncate()
		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].")
			return_code = se.InvalidInputException.code

		if args.verbose:
			console.print(" OK")

	return return_code
