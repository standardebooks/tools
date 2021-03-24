"""
This module implements the `se typogrify` command.
"""

import argparse
import html

from rich.console import Console

import se
import se.typography
import se.easy_xml


def typogrify() -> int:
	"""
	Entry point for `se typogrify`
	"""

	parser = argparse.ArgumentParser(description="Apply some scriptable typography rules from the Standard Ebooks typography manual to XHTML files.")
	parser.add_argument("-n", "--no-quotes", dest="quotes", action="store_false", help="don’t convert to smart quotes before doing other adjustments")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel
	return_code = 0
	ignored_filenames = se.IGNORED_FILENAMES
	ignored_filenames.remove("toc.xhtml")
	ignored_filenames.remove("halftitlepage.xhtml")
	ignored_filenames.remove("loi.xhtml")
	ignored_filenames.remove("colophon.xhtml")

	for filename in se.get_target_filenames(args.targets, (".xhtml", ".opf"), ignored_filenames):
		if args.verbose:
			console.print(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", end="")

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				if filename.name == "content.opf":
					dom = se.easy_xml.EasyOpfTree(xhtml)

					# Typogrify metadata except for URLs, dates, and LoC subjects
					for node in dom.xpath("/package/metadata/dc:*[local-name() != 'subject' and local-name() != 'source' and local-name() != 'date']") + dom.xpath("/package/metadata/meta[not(contains(@property, 'se:url') or @property = 'dcterms:modified' or @property = 'se:production-notes')]"):
						contents = node.lxml_element.text

						if contents:
							contents = html.unescape(contents)

							contents = se.typography.typogrify(contents)

							# Tweak: Word joiners and nbsp don't go in metadata
							contents = contents.replace(se.WORD_JOINER, "")
							contents = contents.replace(se.NO_BREAK_SPACE, " ")

							# Typogrify escapes ampersands, and then lxml will also escape them again, so we unescape them
							# before passing to lxml.
							if node.get_attr("property") != "se:long-description":
								contents = contents.replace("&amp;", "&").strip()

							node.lxml_element.text = contents

					processed_xhtml = dom.to_string()

				else:
					processed_xhtml = se.typography.typogrify(xhtml, args.quotes)

					if filename.name == "toc.xhtml":
						# Tweak: Word joiners and nbsp don't go in the ToC
						processed_xhtml = processed_xhtml.replace(se.WORD_JOINER, "")
						processed_xhtml = processed_xhtml.replace(se.NO_BREAK_SPACE, " ")

				if processed_xhtml != xhtml:
					file.seek(0)
					file.write(processed_xhtml)
					file.truncate()

			if args.verbose:
				console.print(" OK")

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].")
			return_code = se.InvalidInputException.code

	return return_code
