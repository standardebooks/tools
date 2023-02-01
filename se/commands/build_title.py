"""
This module implements the `se build-title` command.
"""

import argparse

import se
import se.easy_xml
import se.formatting


def build_title(plain_output: bool) -> int:
	"""
	Entry point for `se build-title`
	"""

	parser = argparse.ArgumentParser(description="Generate the title of an XHTML file based on its headings and update the file’s <title> element.")
	parser.add_argument("-n", "--no-newline", dest="newline", action="store_false", help="with --stdout, don’t end output with a newline")
	parser.add_argument("-s", "--stdout", action="store_true", help="print to stdout intead of writing to the file")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	targets = se.get_target_filenames(args.targets, ".xhtml")

	if args.stdout and (len(targets) > 1):
		se.print_error("Multiple targets or directories are only allowed without the [bash]--stdout[/] option.", plain_output=plain_output)
		return se.InvalidArgumentsException.code

	if not args.newline and not args.stdout:
		se.print_error("The [bash]--no-newline[/] option can only be used with the [bash]--stdout[/] option.", plain_output=plain_output)

	return_code = 0

	for filename in targets:
		try:
			with open(filename, "r+", encoding="utf-8") as file:
				dom = se.easy_xml.EasyXmlTree(file.read())

				title = se.formatting.generate_title(dom)

				if args.stdout:
					if args.newline:
						print(title)
					else:
						print(title, end="")

				else:
					if title == "":
						se.print_error(f"Couldn’t deduce title for file: [path][link=file://{filename}]{filename}[/][/].", False, True, plain_output=plain_output)
					else:
						if dom:
							for node in dom.xpath("/html/head/title"):
								node.set_text(title)

							file.seek(0)
							file.write(dom.to_string())
							file.truncate()

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code
		except se.SeException as ex:
			se.print_error(f"File: [path][link=file://{filename}]{filename}[/][/]. {ex}", plain_output=plain_output)
			return_code = ex.code

	return return_code
