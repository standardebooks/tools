"""
This module implements the `se british2american` command.
"""

import argparse

import se
from se.se_help_formatter import SeHelpFormatter
import se.typography


def british2american(plain_output: bool) -> int:
	"""
	Entry point for `se british2american`.
	"""

	parser = argparse.ArgumentParser(description="Try to convert British quote style to American quote style. Quotes must already be typogrified using [command]se[/] [subcommand]typogrify[/]. This script isn’t perfect; proofreading is required, especially near closing quotes near to em-dashes.", prog="[command]se[/] [subcommand]british2american[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-f", "--force", action="store_true", help="Force conversion of quote style.")
	parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity.")
	parser.add_argument("targets", metavar="[path]TARGET[/]", nargs="+", help="An XHTML file, or a directory containing XHTML files.")
	args = parser.parse_args()

	return_code = 0
	console = se.init_console()

	for filename in se.get_target_filenames(args.targets, ".xhtml"):
		# Skip the uncopyright, since it contains quotes but is a fixed file.
		if filename.name == "uncopyright.xhtml":
			continue

		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", plain_output), end="")

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
						se.print_error(f"File appears to already use American quote style, ignoring. Use [flag]--force[/] to convert anyway.{f' File: [path][link=file://{filename}]{filename}[/][/]' if not args.verbose else ''}", args.verbose, plain_output=plain_output)

				if convert:
					new_xhtml = se.typography.convert_british_to_american(xhtml)

					if new_xhtml != xhtml:
						file.seek(0)
						file.write(new_xhtml)
						file.truncate()

			if args.verbose:
				console.print(" done.")

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code

	return return_code
