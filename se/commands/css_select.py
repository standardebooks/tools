"""
This module implements the `se css-select` command.
"""

import argparse

from rich.console import Console
import se
import se.easy_xml


def css_select(plain_output: bool) -> int:
	"""
	Entry point for `se css-select`
	"""

	parser = argparse.ArgumentParser(description="Print the results of a CSS selector evaluated against a set of XHTML files.")
	parser.add_argument("-f", "--only-filenames", action="store_true", help="only output filenames of files that contain matches, not the matches themselves")
	parser.add_argument("selector", metavar="SELECTOR", help="a CSS selector")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=True, theme=se.RICH_THEME)

	for filepath in se.get_target_filenames(args.targets, ".xhtml"):
		try:

			with open(filepath, "r", encoding="utf-8") as file:
				dom = se.easy_xml.EasyXmlTree(file.read())

			nodes = dom.css_select(args.selector)

			if nodes:
				console.print(se.prep_output(f"[path][link=file://{filepath}]{filepath}[/][/]", plain_output), highlight=False)
				if not args.only_filenames:
					for node in nodes:
						if isinstance(node, se.easy_xml.EasyXmlElement):
							output = node.to_string()
						else:
							# We may select text() nodes as a result
							output = str(node)

						output = "".join([f"\t{line}\n" for line in output.splitlines()])

						# We only have to escape leading [ to prevent Rich from converting
						# it to a style. If we also escape ] then Rich will print the slash.
						output = output.replace("[", "\\[")

						console.print(output)

		except se.InvalidCssException:
			se.print_error("Invalid CSS selector.")
			return se.InvalidInputException.code

		except se.SeException as ex:
			se.print_error(f"File: [path][link=file://{filepath}]{filepath}[/][/]. Exception: {ex}", plain_output=plain_output)
			return ex.code

	return 0
