"""
This module implements the `se print-title` command.
"""

import argparse

import regex

from roman import InvalidRomanNumeralError
import se
import se.easy_xml
import se.formatting


def print_title() -> int:
	"""
	Entry point for `se print-title`
	"""

	parser = argparse.ArgumentParser(description="Print the expected value for an XHTML file’s <title> element.")
	parser.add_argument("-i", "--in-place", action="store_true", help="replace the file’s <title> element instead of printing to stdout")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	targets = se.get_target_filenames(args.targets, ".xhtml")

	if not args.in_place and (len(targets) > 1):
		se.print_error("Multiple targets or directories are only allowed with the [bash]--in-place[/] option.")
		return se.InvalidArgumentsException.code

	return_code = 0

	for filename in targets:
		try:
			with open(filename, "r+", encoding="utf-8") as file:
				dom = se.easy_xml.EasyXmlTree(file.read())

				title = se.formatting.generate_title(dom)

				if args.in_place:
					if title == "":
						se.print_error(f"Couldn’t deduce title for file: [path][link=file://{filename}]{filename}[/][/].", False, True)
					else:
						if dom:
							for node in dom.xpath("/html/head/title"):
								node.set_text(title)

							file.seek(0)
							file.write(dom.to_string())
							file.truncate()
				else:
					print(title)

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].")
			return_code = se.InvalidInputException.code
		except InvalidRomanNumeralError as ex:
			se.print_error(regex.sub(r"^.+: (.+)$", fr"Invalid Roman numeral: [text]\1[/]. File: [path][link=file://{filename}]{filename}[/][/].", str(ex)))
			return_code = se.InvalidInputException.code
		except se.SeException as ex:
			se.print_error(f"File: [path][link=file://{filename}]{filename}[/][/]. {ex}")
			return_code = ex.code

	return return_code
