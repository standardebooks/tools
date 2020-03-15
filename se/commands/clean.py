"""
This module implements the `se clean` command.
"""

import argparse

import se
import se.formatting


def clean() -> int:
	"""
	Entry point for `se clean`
	"""

	parser = argparse.ArgumentParser(description="Prettify and canonicalize individual XHTML, SVG, or CSS files, or all XHTML, SVG, or CSS files in a source directory. Note that this only prettifies the source code; it doesn’t perform typography changes.")
	parser.add_argument("-s", "--single-lines", action="store_true", help="remove hard line wrapping")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML, SVG, or CSS file, or a directory containing XHTML, SVG, or CSS files")
	args = parser.parse_args()

	for filename in se.get_target_filenames(args.targets, (".xhtml", ".svg", ".opf", ".ncx", ".xml"), []):
		# If we're setting single lines, skip the colophon, as it has special spacing.
		if args.single_lines and filename.name == "colophon.xhtml":
			continue

		if args.verbose:
			print(f"Processing {filename} ...", end="", flush=True)

		try:
			se.formatting.format_xhtml_file(filename, args.single_lines, filename.name == "content.opf", filename.name == "endnotes.xhtml", filename.name == "colophon.xhtml")
		except se.MissingDependencyException as ex:
			se.print_error(ex)
			return ex.code
		except se.SeException as ex:
			se.print_error(f"File: `{filename}`\n{str(ex)}", args.verbose)
			return ex.code

		if args.verbose:
			print(" OK")

	for filename in se.get_target_filenames(args.targets, (".css",), []):
		# Skip core.css as this must be copied in from the template
		if filename.name == "core.css":
			continue

		if args.verbose:
			print(f"Processing {filename} ...", end="", flush=True)

		with open(filename, "r+", encoding="utf-8") as file:
			css = file.read()

			try:
				processed_css = se.formatting.format_css(css)

				if processed_css != css:
					file.seek(0)
					file.write(processed_css)
					file.truncate()
			except se.SeException as ex:
				se.print_error(f"File: `{filename}`\n{str(ex)}", args.verbose)
				return ex.code

		if args.verbose:
			print(" OK")

	return 0
