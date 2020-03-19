"""
This module implements the `se typogrify` command.
"""

import argparse

import se
import se.typography


def typogrify() -> int:
	"""
	Entry point for `se typogrify`
	"""

	parser = argparse.ArgumentParser(description="Apply some scriptable typography rules from the Standard Ebooks typography manual to XHTML files.")
	parser.add_argument("-n", "--no-quotes", dest="quotes", action="store_false", help="don’t convert to smart quotes before doing other adjustments")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	if args.verbose and not args.quotes:
		print("Skipping smart quotes.")

	return_code = 0
	ignored_filenames = se.IGNORED_FILENAMES
	ignored_filenames.remove("toc.xhtml")

	for filename in se.get_target_filenames(args.targets, (".xhtml",), ignored_filenames):
		if filename.name == "titlepage.xhtml":
			continue

		if args.verbose:
			print(f"Processing {filename} ...", end="", flush=True)

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()
				processed_xhtml = se.typography.typogrify(xhtml, args.quotes)

				if processed_xhtml != xhtml:
					file.seek(0)
					file.write(processed_xhtml)
					file.truncate()

			if args.verbose:
				print(" OK")

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: `{filename}`")
			return_code = se.InvalidInputException.code

	return return_code
