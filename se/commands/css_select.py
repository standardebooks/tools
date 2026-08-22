"""
This module implements the `se css-select` command.
"""

import argparse

import se
from se.se_help_formatter import SeHelpFormatter
import se.easy_xml


def css_select(plain_output: bool) -> int:
	"""
	Entry point for `se css-select`.
	"""

	parser = argparse.ArgumentParser(description="Print the results of a CSS selector evaluated against a set of XHTML files.", prog="[command]se[/] [subcommand]css-select[/]", formatter_class=SeHelpFormatter)
	output_group = parser.add_mutually_exclusive_group()
	output_group.add_argument("-f", "--only-filenames", action="store_true", help="Only output filenames of files that contain matches, not the matches themselves.")
	output_group.add_argument("-q", "--quiet", action="store_true", help="Don’t output anything, only a return code if matches exist in any files.")
	parser.add_argument("-n", "--no-line-numbers", action="store_true", help="Don’t output line numbers.")
	parser.add_argument("selector", metavar="SELECTOR", help="A CSS selector.")
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

			nodes = dom.css_select(args.selector)

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
						line_number = node.sourceline if node.sourceline is not None else 1
						results.append((line_number, node.to_string()))

					maximum_label_length = max(len(f"Line {line_number}:") for line_number, _ in results) if not args.no_line_numbers else 0
					for line_number, output in results:
						color_output = not plain_output and se.should_output_color()
						if color_output:
							formatted_output = se.highlight_xml(output)
						else:
							if not plain_output:
								output = output.replace('[', '\\[')

							formatted_output = se.prep_output(output, plain_output)

						if args.no_line_numbers:
							console.print(formatted_output)
							continue

						if not plain_output:
							line_output = f"[path][link=file://{filepath.resolve()}{se.format_line_number(line_number)}]Line {line_number}:[/][/]"
						else:
							line_output = f"Line {line_number}:"

						# Add the minimum number of tabs required to align every result after the longest line label.
						tab_count = 1 + (maximum_label_length // 8) - (len(f"Line {line_number}:") // 8)
						console.print(se.prep_output(line_output, plain_output), end="\t" * tab_count)
						console.print(formatted_output)

				has_previous_file = True

		except se.InvalidCssException as ex:
			se.print_error(ex)
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
