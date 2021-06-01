"""
This module implements the `se typogrify` command.
"""

import argparse
import html

from rich.console import Console

import se
import se.typography
import se.easy_xml


def typogrify(plain_output: bool) -> int:
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

	for filename in se.get_target_filenames(args.targets, (".xhtml", ".opf")):
		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{filename}]{filename}[/][/] ...", plain_output), end="")

		try:
			with open(filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				is_ignored, dom = se.get_dom_if_not_ignored(xhtml, ["titlepage", "imprint", "copyright-page"])

				if not is_ignored:
					if dom:
						# Is this a metadata file?
						# Typogrify metadata except for URLs, dates, and LoC subjects
						if dom.xpath("/package"):
							for node in dom.xpath("/package/metadata/dc:*[normalize-space(.) and local-name() != 'subject' and local-name() != 'source' and local-name() != 'date']") + dom.xpath("/package/metadata/meta[normalize-space(.) and (not(contains(@property, 'se:url') or @property = 'dcterms:modified' or @property = 'se:production-notes'))]"):
								node.text = html.unescape(node.text)

								node.text = se.typography.typogrify(node.text)

								# Tweak: Word joiners and nbsp don't go in metadata
								node.text = node.text.replace(se.WORD_JOINER, "")
								node.text = node.text.replace(se.NO_BREAK_SPACE, " ")

								# Typogrify escapes ampersands, and then lxml will also escape them again, so we unescape them
								# before passing to lxml.
								if node.get_attr("property") != "se:long-description":
									node.text = node.text.replace("&amp;", "&").strip()

								processed_xhtml = dom.to_string()
						else:
							processed_xhtml = se.typography.typogrify(xhtml, args.quotes)

						# Tweak: Word joiners and nbsp don't go in the ToC
						if dom.xpath("/html/body//nav[contains(@epub:type, 'toc')]"):
							processed_xhtml = processed_xhtml.replace(se.WORD_JOINER, "")
							processed_xhtml = processed_xhtml.replace(se.NO_BREAK_SPACE, " ")

					else:
						processed_xhtml = se.typography.typogrify(xhtml, args.quotes)

					if processed_xhtml != xhtml:
						file.seek(0)
						file.write(processed_xhtml)
						file.truncate()

			if args.verbose:
				console.print(" OK")

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code

	return return_code
