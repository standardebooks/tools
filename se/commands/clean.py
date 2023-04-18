"""
This module implements the `se clean` command.
"""

import argparse

from rich.console import Console

import se
import se.formatting


def clean(plain_output: bool) -> int:
	"""
	Entry point for `se clean`
	"""

	parser = argparse.ArgumentParser(description="Prettify and canonicalize individual XHTML, SVG, or CSS files, or all XHTML, SVG, or CSS files in a source directory.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML, SVG, or CSS file, or a directory containing XHTML, SVG, or CSS files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	for filepath in se.get_target_filenames(args.targets, (".xhtml", ".svg", ".opf", ".ncx", ".xml", ".css")):
		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{filepath}]{filepath}[/][/] ...", plain_output), end="")

		if filepath.suffix == ".css":
			with open(filepath, "r+", encoding="utf-8") as file:
				css = file.read()

				try:
					processed_css = se.formatting.format_css(css)

					if processed_css != css:
						file.seek(0)
						file.write(processed_css)
						file.truncate()
				except se.SeException as ex:
					se.print_error(f"File: [path][link=file://{filepath}]{filepath}[/][/]. Exception: {ex}", args.verbose, plain_output=plain_output)
					return ex.code

		else:
			try:
				se.formatting.format_xml_file(filepath)
			except se.MissingDependencyException as ex:
				se.print_error(ex, plain_output=plain_output)
				return ex.code
			except se.SeException as ex:
				se.print_error(f"File: [path][link=file://{filepath}]{filepath}[/][/]. Exception: {ex}", args.verbose, plain_output=plain_output)
				return ex.code
			except FileNotFoundError:
				se.print_error(f"Invalid file: [path][link=file://{filepath}]{filepath}[/][/].", args.verbose, plain_output=plain_output)
				return se.InvalidFileException.code

		if args.verbose:
			console.print(" OK")

	return 0
