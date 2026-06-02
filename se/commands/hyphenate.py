"""
This module implements the `se hyphenate` command.
"""

import argparse

import se
from se.se_help_formatter import SeHelpFormatter
import se.typography


def hyphenate(plain_output: bool) -> int:
	"""
	Entry point for `se hyphenate`.
	"""

	parser = argparse.ArgumentParser(description="Insert soft hyphens at syllable breaks in XHTML files.", prog="[command]se[/] [subcommand]hyphenate[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-i", "--ignore-h-tags", action="store_true", help="Don’t add soft hyphens to text in [xhtml]<h1-6>[/] tags.")
	parser.add_argument("-l", "--language", action="store", help="Specify the language for the XHTML files; if unspecified, defaults to the [attr]xml:lang[/] or [attr]lang[/] attribute of the root [xhtml]<html>[/] element.")
	parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity.")
	parser.add_argument("targets", metavar="[path]TARGET[/]", nargs="+", help="An XHTML file, or a directory containing XHTML files.")
	args = parser.parse_args()

	console = se.init_console()

	for filename in se.get_target_filenames(args.targets, ".xhtml"):
		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", plain_output), end="")

		with open(filename, "r+", encoding="utf-8") as file:
			xhtml = file.read()

			is_ignored, dom = se.get_dom_if_not_ignored(xhtml, ["toc"])

			if not is_ignored and dom:
				processed_xhtml = se.typography.hyphenate(dom, args.language, args.ignore_h_tags)

				if processed_xhtml != xhtml:
					file.seek(0)
					file.write(processed_xhtml)
					file.truncate()

		if args.verbose:
			console.print(" OK")

	return 0
