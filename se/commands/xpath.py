"""
This module implements the `se xpath` command.
"""

import argparse
from typing import Any, Protocol, cast

from lxml import etree
import se
from se.se_help_formatter import SeHelpFormatter
import se.easy_xml


class XPathStringParent(Protocol):
	"""Describe the parent information exposed by an XPath string result."""

	sourceline: int | None


class XPathString(Protocol):
	"""Describe the lxml smart string interface used by this command."""

	def getparent(self) -> XPathStringParent | None:
		"""Return the element from which the XPath string result originated."""


def xpath(plain_output: bool) -> int:
	"""
	Entry point for `se xpath`.
	"""

	parser = argparse.ArgumentParser(description="Print the results of an xpath expression evaluated against a set of XHTML files. The default namespace is removed.", prog="[command]se[/] [subcommand]xpath[/]", formatter_class=SeHelpFormatter)
	output_group = parser.add_mutually_exclusive_group()
	output_group.add_argument("-f", "--only-filenames", action="store_true", help="Only output filenames of files that contain matches, not the matches themselves.")
	output_group.add_argument("-q", "--quiet", action="store_true", help="Don’t output anything, only a return code if matches exist in any files.")
	parser.add_argument("xpath", metavar="XPATH", help="An xpath expression.")
	parser.add_argument("targets", metavar="[path]TARGET[/]", nargs="+", help="An XHTML file, or a directory containing XHTML files.")
	args = parser.parse_args()

	console = se.init_console()

	return_code = 0
	has_results = False
	has_previous_file = False

	for filepath in se.get_target_filenames(args.targets, ".xhtml"):
		try:

			with open(filepath, "r", encoding="utf-8") as file:
				dom = se.easy_xml.EasyXmlTree(file.read())

			nodes = dom.xpath(args.xpath, Any)

			if nodes:
				has_results = True

				if args.quiet:
					# Quit early without printing anything.
					break

				if has_previous_file:
					console.print("")

				console.print(se.prep_output(f"[path][link=file://{filepath}]{filepath}[/][/]", plain_output))
				if not args.only_filenames:
					results: list[tuple[int, str]] = []
					for node in nodes:
						line_number = 1
						output = ""

						# We only have to escape leading `[` to prevent Rich from converting it to a style. If we also escape `]` then Rich will print the slash.
						if isinstance(node, se.easy_xml.EasyXmlElement):
							line_number = node.sourceline if node.sourceline is not None else line_number
							output = node.to_string()

						elif isinstance(node, str):
							parent = cast(XPathString, node).getparent() if hasattr(node, "getparent") else None
							if parent is not None and parent.sourceline is not None:
								line_number = parent.sourceline
							output = node

						elif isinstance(node, float):
							output = str(node)

						elif isinstance(node, etree.Element):
							parent = node.getparent()
							if parent:
								line_number = parent.sourceline if parent.sourceline is not None else line_number
								output = str(node)

						results.append((line_number, output))

					maximum_label_length = max(len(f"Line {line_number}:") for line_number, _ in results)
					for line_number, output in results:
						if not plain_output:
							output = output.replace('[', '\\[')
							line_output = f"[path][link=file://{filepath.resolve()}{se.format_line_number(line_number)}]Line {line_number}:[/][/]"
						else:
							line_output = f"Line {line_number}:"

						# Add the minimum number of tabs required to align every result after the longest line label.
						tab_count = 1 + (maximum_label_length // 8) - (len(f"Line {line_number}:") // 8)
						console.print(se.prep_output(line_output, plain_output), end="\t" * tab_count)
						console.print(se.prep_output(output, plain_output))

				has_previous_file = True

		except etree.XPathEvalError:
			se.print_error("Invalid xpath expression.", plain_output=plain_output)
			return se.InvalidInputException.code

		except se.SeException as ex:
			se.print_error(f"File: [path][link=file://{filepath}]{filepath}[/][/]: {ex}", plain_output=plain_output)
			return ex.code

		except FileNotFoundError:
			se.print_error(f"Invalid file: [path][link=file://{filepath}]{filepath}[/][/].", plain_output=plain_output)
			return se.InvalidFileException.code

	if not has_results:
		return_code = se.NoResults.code

	return return_code
