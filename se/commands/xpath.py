"""
This module implements the `se xpath` command.
"""

import argparse

from lxml import etree
from rich.console import Console
import se
import se.easy_xml


def xpath(plain_output: bool) -> int:
	"""
	Entry point for `se xpath`
	"""

	parser = argparse.ArgumentParser(description="Print the results of an xpath expression evaluated against a set of XHTML files. The default namespace is removed.")
	parser.add_argument("-f", "--only-filenames", action="store_true", help="only output filenames of files that contain matches, not the matches themselves")
	parser.add_argument("xpath", metavar="XPATH", help="an xpath expression")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=True, theme=se.RICH_THEME)

	for filepath in se.get_target_filenames(args.targets, ".xhtml"):
		try:

			with open(filepath, "r", encoding="utf-8") as file:
				dom = se.easy_xml.EasyXmlTree(file.read())

			nodes = dom.xpath(args.xpath)

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

		except etree.XPathEvalError:
			se.print_error("Invalid xpath expression.")
			return se.InvalidInputException.code

		except se.SeException as ex:
			se.print_error(f"File: [path][link=file://{filepath}]{filepath}[/][/]. Exception: {ex}", plain_output=plain_output)
			return ex.code

		except FileNotFoundError:
			se.print_error(f"Invalid file: [path][link=file://{filepath}]{filepath}[/][/].")
			return se.InvalidFileException.code

	return 0
