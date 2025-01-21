"""
This module implements the `se convert-drama` command.
"""

import argparse
from pathlib import Path
import regex

from rich.console import Console
from lxml import etree

import se
import se.easy_xml
import se.formatting

TABLE_CLASS = "drama-table"
TABLE_ROW_CLASS = "drama-row"
TABLE_CELL_CLASS = "drama-cell"

def convert_drama(plain_output: bool) -> int:
	"""
	Entry point for `se convert-drama`
	"""

	parser = argparse.ArgumentParser(description="Convert older-style drama tables to new markup standard.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel
	return_code = 0

	for directory in args.directories:
		directory = Path(directory).resolve()

		has_multiple_speakers_in_one_cell = False

		## Adjust markup
		for filename in se.get_target_filenames([directory], (".xhtml")):
			if args.verbose:
				console.print(se.prep_output(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", plain_output), end="")

			try:
				with open(filename, "r+", encoding="utf-8") as file:
					xhtml = file.read()
					processed_xhtml = xhtml
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

									# try to automatically fix rowspans
									rowspan = row.xpath('.//@rowspan')
									if rowspan:
										print("Attempting to convert rowspans with together blocks, PLEASE double check that this worked OK.")
										has_multiple_speakers_in_one_cell = True
										rowspan_steps = int(rowspan[0]) - 1
										persona_cell = row.xpath('.//*[1]')[0]

										personas = [persona_cell.inner_xml()]

										# Collect personas from the following lines and delete them
										while rowspan_steps:
											next_row = row.xpath('following-sibling::*')[0]
											personas.append(next_row.xpath('.//*[1]')[0].inner_xml())
											next_row.remove()
											rowspan_steps = rowspan_steps - 1

										# Replace the initial cell with the collected list of personas
										persona_cell.set_text('')
										persona_cell.remove_attr_value('epub:type', 'z3998:persona')
										for persona in personas:
											persona_cell.append(etree.fromstring(f'<b xmlns:epub="http://www.idpf.org/2007/ops" epub:type="z3998:persona">{persona}</b>'))
											etree.indent(persona_cell.lxml_element)

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

		# Adjust CSS
		filename = directory / "src" / "epub" / "css" / "local.css"
		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", plain_output), end="")

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				css = file.read()
				processed_css = css

				# standard drama styles
				processed_css = regex.sub(r"\[epub\|type~=\"z3998:drama\"\] table", fr'[epub|type~="z3998:drama"] .{TABLE_CLASS}', processed_css)
				processed_css = regex.sub(r"table\[epub\|type~=\"z3998:drama\"\]", fr'.{TABLE_CLASS}[epub|type~="z3998:drama"]', processed_css)
				processed_css = regex.sub(fr"\.{TABLE_CLASS}(.*?)border-collapse: collapse;", fr".{TABLE_CLASS}\1display: table;", processed_css, flags=regex.DOTALL)

				while regex.search(r"\[epub\|type~=\"z3998:drama\"\](.*?)tr", processed_css):
					processed_css = regex.sub(r"\[epub\|type~=\"z3998:drama\"\](.*?)tr", fr'[epub|type~="z3998:drama"]\1.{TABLE_ROW_CLASS}', processed_css)
				base_drama_row_rule = fr"\[epub\|type~=\"z3998:drama\"\] \.{TABLE_ROW_CLASS}{{"
				if regex.search(base_drama_row_rule, processed_css) is not None:
					processed_css = regex.sub(fr"({base_drama_row_rule}\n\t)", r"\1display: table-row;", processed_css, flags=regex.DOTALL)
				else:
					console.print(f"Added {base_drama_row_rule.replace('\\', '')}}} rule to end of local.css, please move it to an appropriate place in the CSS.")
					processed_css += f"{base_drama_row_rule.replace('\\', '')}display: table-row;}}"

				while regex.search(r"\[epub\|type~=\"z3998:drama\"\](.*?)td", processed_css):
					processed_css = regex.sub(r"\[epub\|type~=\"z3998:drama\"\](.*?)td", fr'[epub|type~="z3998:drama"]\1.{TABLE_CELL_CLASS}', processed_css)
				base_drama_cell_rule = fr"\[epub\|type~=\"z3998:drama\"\] \.{TABLE_CELL_CLASS}{{"
				if regex.search(base_drama_cell_rule, processed_css) is not None:
					processed_css = regex.sub(fr"({base_drama_cell_rule}\n\t)", r"\1display: table-cell;", processed_css, flags=regex.DOTALL)
				else:
					console.print(f"Added {base_drama_cell_rule.replace('\\', '')}}} rule to end of local.css, please move it to an appropriate place in the CSS.")
					processed_css += f"{base_drama_cell_rule.replace('\\', '')}display: table-cell;}}"

				# process old persona-specific styles to be applied to :first-child
				processed_css = regex.sub(r"\[epub\|type~=\"z3998:drama\"\] .drama-cell:first-child\{", "[epub|type~=\"z3998:drama\"] .drama-cell:first-child{text-align:right;width:20%;", processed_css)
				processed_css = regex.sub(r"(\[epub\|type~=\"z3998:drama\"\] .drama-cell\[epub\|type~=\"z3998:persona\"\]\{\n\thyphens: none;\n\t-epub-hyphens: none;)\n\ttext-align: right;\n\twidth: 20%;", r"\1", processed_css, flags=regex.DOTALL)

				# together styles
				processed_css = regex.sub(r"(?:tr)?\.together(.*?)", fr'.{TABLE_ROW_CLASS}.together\1', processed_css)
				while regex.search(r"together.*?td", processed_css):
					processed_css = regex.sub(r"(?:tr)?\.together(.*?)td( + td)?", fr'.together\1.{TABLE_CELL_CLASS}', processed_css)
				if has_multiple_speakers_in_one_cell:
					multiple_persona_cell_rull = fr"\[epub\|type~=\"z3998:drama\"\] \.{TABLE_CELL_CLASS}:first-child > b\[epub\|type~=\"z3998:persona\"\]{{"
					console.print(f"Added {multiple_persona_cell_rull.replace('\\', '')}}} rule to end of local.css, please move it to an appropriate place in the CSS.")
					processed_css += f"{multiple_persona_cell_rull.replace('\\', '')}display: block;}}"

				processed_css = se.formatting.format_css(processed_css)

				if processed_css != css:
					file.seek(0)
					file.write(processed_css)
					file.truncate()

			if args.verbose:
				console.print(" OK")

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code

	return return_code
