"""
This module implements the `se print-title` command.
"""

import argparse

import regex

import se
import se.formatting


def print_title() -> int:
	"""
	Entry point for `se print-title`
	"""

	parser = argparse.ArgumentParser(description="Print the expected value for an XHTML file’s <title> element.")
	parser.add_argument("-i", "--in-place", action="store_true", help="replace the file’s <title> element instead of printing to stdout")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	if not args.in_place and len(args.targets) > 1:
		se.print_error("Multiple targets are only allowed with the `--in-place` option.")
		return se.InvalidArgumentsException.code

	return_code = 0

	for filename in se.get_target_filenames(args.targets, (".xhtml",)):
		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				title = se.formatting.generate_title(xhtml)

				if args.in_place:
					processed_xhtml = regex.sub(r"<title>(.+?)</title>", f"<title>{title}</title>", xhtml)

					if processed_xhtml != xhtml:
						file.seek(0)
						file.write(processed_xhtml)
						file.truncate()
				else:
					print(title)

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: `{filename}`")
			return_code = se.InvalidInputException.code
		except se.SeException as ex:
			se.print_error(ex)
			return_code = ex.code

	return return_code
