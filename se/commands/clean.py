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
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML, SVG, or CSS file, or a directory containing XHTML, SVG, or CSS files")
	args = parser.parse_args()

	for filepath in se.get_target_filenames(args.targets, (".xhtml", ".svg", ".opf", ".ncx", ".xml"), []):
		if args.verbose:
			print(f"Processing {filepath} ...", end="", flush=True)

		try:
			se.formatting.format_xml_file(filepath)
		except se.MissingDependencyException as ex:
			se.print_error(ex)
			return ex.code
		except se.SeException as ex:
			se.print_error(f"File: `{filepath}`\n{str(ex)}", args.verbose)
			return ex.code

		if args.verbose:
			print(" OK")

	for filepath in se.get_target_filenames(args.targets, (".css",), []):
		# Skip core.css as this must be copied in from the template
		if filepath.name == "core.css":
			continue

		if args.verbose:
			print(f"Processing {filepath} ...", end="", flush=True)

		with open(filepath, "r+", encoding="utf-8") as file:
			css = file.read()

			try:
				processed_css = se.formatting.format_css(css)

				if processed_css != css:
					file.seek(0)
					file.write(processed_css)
					file.truncate()
			except se.SeException as ex:
				se.print_error(f"File: `{filepath}`\n{str(ex)}", args.verbose)
				return ex.code

		if args.verbose:
			print(" OK")

	return 0
