"""
This module implements the `se british2american` command.
"""

import argparse

from rich.console import Console

import se
import se.typography


def british2american() -> int:
	"""
	Entry point for `se british2american`
	"""

	parser = argparse.ArgumentParser(description="Try to convert British quote style to American quote style. Quotes must already be typogrified using the `typogrify` tool. This script isn’t perfect; proofreading is required, especially near closing quotes near to em-dashes.")
	parser.add_argument("-f", "--force", action="store_true", help="force conversion of quote style")
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
				new_xhtml = xhtml

				convert = True
				if not args.force:
					if se.typography.guess_quoting_style(xhtml) == "american":
						convert = False
						if args.verbose:
							console.print("")
						se.print_error(f"File appears to already use American quote style, ignoring. Use [bash]--force[/] to convert anyway.{f' File: [path][link=file://{filename}]{filename}[/][/]' if not args.verbose else ''}", args.verbose, True)

				if convert:
					new_xhtml = se.typography.convert_british_to_american(xhtml)

					if new_xhtml != xhtml:
						file.seek(0)
						file.write(new_xhtml)
						file.truncate()

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].")
			return_code = se.InvalidInputException.code

	return return_code
