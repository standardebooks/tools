"""
This module implements the `se convert-drama` command.
"""

import argparse
import html
from pathlib import Path

from rich.console import Console

import se
import se.easy_xml
import se.formatting


def convert_drama(plain_output: bool) -> int:
	"""
	Entry point for `se convert-drama`
	"""

	TABLE_CLASS = "drama-table"
	TABLE_ROW_CLASS = "drama-row"
	TABLE_CELL_CLASS = "drama-cell"

	parser = argparse.ArgumentParser(description="Convert older-style drama tables to new markup standard.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel
	return_code = 0

	for directory in args.directories:
		directory = Path(directory).resolve()

		## Adjust markup
		for filename in se.get_target_filenames([directory], (".xhtml")):
			if args.verbose:
				console.print(se.prep_output(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", plain_output), end="")

			try:
				with open(filename, "r+", encoding="utf-8") as file:
					xhtml = file.read()
					is_ignored, dom = se.get_dom_if_not_ignored(xhtml, ["colophon", "titlepage", "imprint", "copyright-page", "halftitlepage", "toc", "loi"])

					if not is_ignored:
						if dom:
							for table in dom.xpath("/html/body//table[./ancestor-or-self::*[contains(@epub:type, 'z3998:drama')]]"):
								# Convert <table> to <div class="drama-table">
								table.lxml_element.tag = "div"
								table.add_attr_value("class", TABLE_CLASS)

								rows = table.xpath('.//tr')
								for index, row in enumerate(rows):
									if index == 0:
										row.parent.unwrap()
									row.lxml_element.tag = "div"
									row.add_attr_value("class", TABLE_ROW_CLASS)

									cells = row.xpath('./td')

									for cell in cells:
										cell.lxml_element.tag = "div"
										cell.add_attr_value("class", TABLE_CELL_CLASS)

							processed_xhtml = dom.to_string()

						if processed_xhtml != xhtml:
							file.seek(0)
							file.write(processed_xhtml)
							file.truncate()

							try:
								se.formatting.format_xml_file(filename)
							except se.MissingDependencyException as ex:
								se.print_error(ex, plain_output=plain_output)
								return ex.code
							except se.SeException as ex:
								se.print_error(f"File: [path][link=file://{filename}]{filename}[/][/]. Exception: {ex}", args.verbose, plain_output=plain_output)
								return ex.code

				if args.verbose:
					console.print(" OK")

			except FileNotFoundError:
				se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
				return_code = se.InvalidInputException.code

	return return_code
