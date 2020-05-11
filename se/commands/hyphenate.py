"""
This module implements the `se hyphenate` command.
"""

import argparse

from rich.console import Console

import se
import se.typography


def hyphenate() -> int:
	"""
	Entry point for `se hyphenate`
	"""

	parser = argparse.ArgumentParser(description="Insert soft hyphens at syllable breaks in XHTML files.")
	parser.add_argument("-i", "--ignore-h-tags", action="store_true", help="don’t add soft hyphens to text in <h1-6> tags")
	parser.add_argument("-l", "--language", action="store", help="specify the language for the XHTML files; if unspecified, defaults to the `xml:lang` or `lang` attribute of the root <html> element")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	for filename in se.get_target_filenames(args.targets, (".xhtml",)):
		if args.verbose:
			console.print(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", end="")

		se.typography.hyphenate_file(filename, args.language, args.ignore_h_tags)

		if args.verbose:
			console.print(" OK")

	return 0
