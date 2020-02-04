"""
typogrify command
"""

import argparse

import se
from se.typography import typogrify
from se.common import get_target_filenames, print_error


def cmd_typogrify() -> int:
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

	ignored_filenames = se.IGNORED_FILENAMES
	ignored_filenames.remove("toc.xhtml")

	for filename in get_target_filenames(args.targets, (".xhtml",), ignored_filenames):
		if filename.name == "titlepage.xhtml":
			continue

		if args.verbose:
			print(f"Processing {filename} ...", end="", flush=True)

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()
				processed_xhtml = typogrify(xhtml, args.quotes)

				if processed_xhtml != xhtml:
					file.seek(0)
					file.write(processed_xhtml)
					file.truncate()

			if args.verbose:
				print(" OK")

		except FileNotFoundError:
			print_error(f"Not a file: {filename}")
			return se.InvalidFileException.code

	return 0
