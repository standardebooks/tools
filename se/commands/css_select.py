"""
This module implements the `se css-select` command.
"""

import argparse

import se
import se.easy_xml


def css_select(plain_output: bool) -> int:
	"""
	Entry point for `se css-select`.
	"""

	parser = argparse.ArgumentParser(description="Print the results of a CSS selector evaluated against a set of XHTML files.")
	parser.add_argument("-f", "--only-filenames", action="store_true", help="only output filenames of files that contain matches, not the matches themselves")
	parser.add_argument("selector", metavar="SELECTOR", help="a CSS selector")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = se.init_console()

	return_code = 0
	has_results = False

	for filepath in se.get_target_filenames(args.targets, ".xhtml"):
		try:
			with open(filepath, "r", encoding="utf-8") as file:
				dom = se.easy_xml.EasyXmlTree(file.read())

			nodes = dom.css_select(args.selector)

			if nodes:
				has_results = True
				console.print(se.prep_output(f"[path][link=file://{filepath}]{filepath}[/][/]", plain_output))
				if not args.only_filenames:
					for node in nodes:
						if isinstance(node, se.easy_xml.EasyXmlElement):
							if plain_output:
								output = f"Line {node.sourceline}: {node.to_string()}"
							else:
								output = f"[path][link=file://{filepath.resolve()}#L{node.sourceline}]Line {node.sourceline}[/][/]: {node.to_string().replace('[', '\\[')}"
						else:
							# We may select `text()` nodes as a result.
							if plain_output:
								output = f"Line {node.getparent().sourceline}: {str(node)}"
							else:
								output = f"[path][link=file://{filepath.resolve()}#L{node.getparent().sourceline}]Line {node.getparent().sourceline}[/][/]: {str(node).replace('[', '\\[')}"


						output = "".join([f"\t{line}\n" for line in output.splitlines()])

						console.print(output, plain_output)

		except se.InvalidCssException as ex:
			se.print_error(ex)
			return se.InvalidInputException.code

		except se.SeException as ex:
			se.print_error(f"File: [path][link=file://{filepath}]{filepath}[/][/]. Exception: {ex}", plain_output=plain_output)
			return ex.code

		except FileNotFoundError:
			se.print_error(f"Invalid file: [path][link=file://{filepath}]{filepath}[/][/].", plain_output=plain_output)
			return se.InvalidFileException.code


	if not has_results:
		return_code = se.NoResults.code

	return return_code
