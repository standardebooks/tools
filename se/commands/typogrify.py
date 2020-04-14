"""
This module implements the `se typogrify` command.
"""

import argparse
import html
from pathlib import Path

import regex

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

	for filename in se.get_target_filenames(args.targets, (".xhtml", ".opf"), ignored_filenames):
		if args.verbose:
			print(f"Processing {filename} ...", end="", flush=True)

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				if Path(filename).name == "content.opf":
					processed_xhtml = xhtml

					# Extract the long description
					matches = regex.search(r"""<meta(?:[^<]*?)property="se:long-description"(?:[^<]*?)>(.+?)</meta>""", xhtml, flags=regex.DOTALL)

					if matches:
						long_description = matches[1].strip()

						processed_long_description = html.unescape(long_description)

						processed_long_description = se.typography.typogrify(long_description)

						# Tweak: Word joiners don't go in the long description
						processed_long_description = processed_long_description.replace(se.WORD_JOINER, "")

						processed_long_description = html.escape(processed_long_description)

						processed_xhtml = xhtml.replace(long_description, processed_long_description)

					# Extract the regular description
					matches = regex.search(r"""<dc:description(?:[^<]*?)>(.+?)</dc:description>""", xhtml, flags=regex.DOTALL)

					if matches:
						description = matches[1].strip()
						processed_description = se.typography.typogrify(description)

						# Tweak: Word joiners don't go in the long description
						processed_description = processed_description.replace(se.WORD_JOINER, "")

						processed_xhtml = processed_xhtml.replace(description, processed_description)
				else:
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
