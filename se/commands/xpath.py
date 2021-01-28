"""
This module implements the `se xpath` command.
"""

import argparse

from lxml import etree
from rich.console import Console
import se
import se.easy_xml


def xpath() -> int:
	"""
	Entry point for `se xpath`
	"""

	parser = argparse.ArgumentParser(description="Print the results of an xpath expression evaluated against a set of XHTML files. The default namespace is removed.")
	parser.add_argument("xpath", metavar="XPATH", help="an xpath expression")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=True, theme=se.RICH_THEME)

	for filepath in se.get_target_filenames(args.targets, ".xhtml", []):
		try:
			with open(filepath, 'r') as file:
				dom = se.easy_xml.EasyXhtmlTree(file.read())

			nodes = dom.xpath(args.xpath)

			if nodes:
				console.print(f"[path][link=file://{filepath}]{filepath}[/][/]", highlight=False)
				for node in nodes:
					mystring = "".join([f"\t{line}\n" for line in node.to_string().splitlines()])
					console.print(mystring)

		except etree.XPathEvalError as ex:
			se.print_error("Invalid xpath expression.")
			return se.InvalidInputException.code

		except se.SeException as ex:
			se.print_error(f"File: [path][link=file://{filepath}]{filepath}[/][/]. Exception: {ex}")
			return ex.code

	return 0
